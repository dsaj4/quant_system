from datetime import datetime
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.database import SessionDep
from app.core.security import get_current_user
from app.models import (
    BacktestRun,
    PublishedSnapshot,
    ShareLink,
    SnapshotStatus,
    TaskStatus,
    User,
    utc_now,
)
from app.services.narratives import build_public_narrative_payload, get_current_narrative_for_backtest
from app.services.operation_log import record_operation

router = APIRouter(tags=["snapshots"])


class SnapshotPublishRequest(BaseModel):
    backtest_run_id: int
    title: str = Field(min_length=1)


class SnapshotResponse(BaseModel):
    id: int
    backtest_run_id: int
    version: int
    status: SnapshotStatus
    title: str
    immutable_payload: dict
    published_at: datetime | None
    created_at: datetime


class SnapshotPublishResponse(BaseModel):
    snapshot: SnapshotResponse
    share_token: str


class ShareLinkResponse(BaseModel):
    id: int
    snapshot_id: int
    snapshot_title: str
    snapshot_status: SnapshotStatus
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class ShareLinkCreateResponse(BaseModel):
    share_link: ShareLinkResponse
    share_token: str


class PublicSnapshotResponse(BaseModel):
    id: int
    title: str
    version: int
    payload: dict
    published_at: datetime | None


def hash_share_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def snapshot_response(snapshot: PublishedSnapshot) -> SnapshotResponse:
    return SnapshotResponse(
        id=snapshot.id or 0,
        backtest_run_id=snapshot.backtest_run_id,
        version=snapshot.version,
        status=snapshot.status,
        title=snapshot.title,
        immutable_payload=snapshot.immutable_payload,
        published_at=snapshot.published_at,
        created_at=snapshot.created_at,
    )


def share_link_response(share_link: ShareLink, snapshot: PublishedSnapshot) -> ShareLinkResponse:
    return ShareLinkResponse(
        id=share_link.id or 0,
        snapshot_id=snapshot.id or 0,
        snapshot_title=snapshot.title,
        snapshot_status=snapshot.status,
        is_active=share_link.is_active,
        expires_at=share_link.expires_at,
        created_at=share_link.created_at,
    )


def create_share_link_for_snapshot(snapshot: PublishedSnapshot) -> tuple[ShareLink, str]:
    share_token = secrets.token_urlsafe(24)
    share_link = ShareLink(
        snapshot_id=snapshot.id or 0,
        token_hash=hash_share_token(share_token),
        is_active=True,
    )
    return share_link, share_token


def extract_backtest_period(result_payload: dict) -> dict:
    series = result_payload.get("equity_curve") or result_payload.get("candles") or []
    timestamps = [point.get("timestamp") for point in series if isinstance(point, dict) and point.get("timestamp")]
    return {
        "start": timestamps[0] if timestamps else None,
        "end": timestamps[-1] if timestamps else None,
    }


def build_report_metadata(backtest: BacktestRun, title: str, publisher: User) -> dict:
    config = backtest.config or {}
    metrics = backtest.metrics or {}
    result_payload = backtest.result_payload or {}
    scope = config.get("scope") or ("portfolio" if config.get("portfolio_id") else "instrument")
    target_label = (
        config.get("portfolio_name")
        or config.get("instrument_symbol")
        or (f"固定组合 #{config.get('portfolio_id')}" if config.get("portfolio_id") else None)
        or (f"标的 #{config.get('instrument_id')}" if config.get("instrument_id") else "未记录标的")
    )
    bar_count = int(metrics.get("bar_count") or 0)
    missing_sections = [
        section
        for section in ("equity_curve", "benchmark_curve", "drawdown_curve", "candles", "position_curve", "trade_table")
        if not result_payload.get(section)
    ]
    warnings = []
    if bar_count < 30:
        warnings.append("样本K线数量较少，展示结果仅适合作为流程演示或初步观察。")
    if missing_sections:
        warnings.append("部分展示数据缺失：" + "、".join(missing_sections))
    data_quality = result_payload.get("data_quality") or {}
    warnings.extend(data_quality.get("warnings") or [])

    return {
        "title": title,
        "strategy_id": backtest.strategy_id,
        "strategy_version": "0.1.0",
        "snapshot_status": "published",
        "scope": scope,
        "scope_label": "固定组合" if scope == "portfolio" else "单支股票",
        "target_label": target_label,
        "frequency": config.get("frequency", "5m"),
        "initial_cash": config.get("initial_cash"),
        "backtest_period": extract_backtest_period(result_payload),
        "generated_at": utc_now().isoformat(),
        "publisher": publisher.username,
        "warnings": warnings,
        "missing_sections": missing_sections,
    }


def build_report_assumptions(backtest: BacktestRun) -> dict:
    config = backtest.config or {}
    result_payload = backtest.result_payload or {}
    execution_assumptions = result_payload.get("execution_assumptions") or {}
    return {
        "data_source": config.get("data_source", "stored_bars"),
        "execution_model": "V2资金仓位回测，按已存储K线、目标仓位、手续费和滑点假设生成模拟成交。",
        "fees_included": bool(execution_assumptions.get("fees_included")),
        "slippage_included": bool(execution_assumptions.get("slippage_included")),
        "fee_rate": execution_assumptions.get("fee_rate", 0),
        "slippage_bps": execution_assumptions.get("slippage_bps", 0),
        "benchmark_method": "基准曲线按首根K线买入持有估算，用于对照策略权益变化。",
        "frequency": config.get("frequency", "5m"),
        "live_trading": False,
    }


def build_data_quality_summary(backtest: BacktestRun) -> dict:
    result_payload = backtest.result_payload or {}
    payload_quality = result_payload.get("data_quality")
    if isinstance(payload_quality, dict) and payload_quality:
        bar_count = int(payload_quality.get("bar_count") or (backtest.metrics or {}).get("bar_count") or 0)
        warnings = payload_quality.get("warnings") or []
        return {
            **payload_quality,
            "bar_count": bar_count,
            "sample_warning": bool(payload_quality.get("sample_warning")) or bar_count < 30,
            "warnings": warnings,
        }

    bar_count = int((backtest.metrics or {}).get("bar_count") or 0)
    if bar_count == 0:
        status = "empty"
    elif bar_count < 30:
        status = "warning"
    else:
        status = "ok"

    return {
        "status": status,
        "bar_count": bar_count,
        "sample_warning": bar_count < 30,
        "message": "样本K线数量较少。" if bar_count < 30 else "样本数量满足基础展示要求。",
        "warnings": ["样本K线数量较少。"] if bar_count < 30 else [],
    }


def build_report_summary(backtest: BacktestRun) -> dict:
    metrics = backtest.metrics or {}
    config = backtest.config or {}
    cumulative_return = metrics.get("cumulative_return")
    max_drawdown = metrics.get("max_drawdown")
    annualized_return = metrics.get("annualized_return")
    trade_count = int(metrics.get("trade_count") or 0)
    target = (
        config.get("portfolio_name")
        or config.get("instrument_symbol")
        or (f"组合 #{config.get('portfolio_id')}" if config.get("portfolio_id") else None)
        or (f"标的 #{config.get('instrument_id')}" if config.get("instrument_id") else "当前标的")
    )

    return {
        "performance_summary": (
            f"{target} 本次回测累计收益为 {cumulative_return:.2%}，"
            f"年化收益为 {annualized_return:.2%}。"
            if isinstance(cumulative_return, int | float) and isinstance(annualized_return, int | float)
            else f"{target} 本次回测已生成，但收益指标不完整。"
        ),
        "risk_summary": (
            f"最大回撤为 {max_drawdown:.2%}，需要结合样本区间和市场环境解读。"
            if isinstance(max_drawdown, int | float)
            else "最大回撤指标暂缺，需要结合原始曲线解读。"
        ),
        "method_summary": (
            f"报告基于已发布快照生成，周期为 {config.get('frequency', '未记录')}，"
            f"复权参数为 {config.get('adjust') if config.get('adjust') is not None else '未指定'}，"
            f"共记录 {trade_count} 笔模拟交易。"
        ),
    }


def build_data_summary(backtest: BacktestRun) -> dict:
    config = backtest.config or {}
    metrics = backtest.metrics or {}
    result_payload = backtest.result_payload or {}
    period = extract_backtest_period(result_payload)
    return {
        "data_source": config.get("data_source", "stored_bars"),
        "provider": config.get("provider") or config.get("data_provider") or config.get("data_source", "stored_bars"),
        "frequency": config.get("frequency", "5m"),
        "adjust": config.get("adjust"),
        "bar_count": int(metrics.get("bar_count") or 0),
        "period_start": period.get("start"),
        "period_end": period.get("end"),
    }


def build_risk_metrics(backtest: BacktestRun) -> dict:
    metrics = backtest.metrics or {}
    return {
        "max_drawdown": metrics.get("max_drawdown", 0),
        "annualized_volatility": metrics.get("annualized_volatility", 0),
        "sharpe_ratio": metrics.get("sharpe_ratio", 0),
        "calmar_ratio": metrics.get("calmar_ratio", 0),
        "return_drawdown_ratio": metrics.get("return_drawdown_ratio", 0),
    }


def build_trade_summary(backtest: BacktestRun) -> dict:
    metrics = backtest.metrics or {}
    result_payload = backtest.result_payload or {}
    trade_table = result_payload.get("trade_table") or []
    buy_count = 0
    sell_count = 0
    timestamps = []
    for trade in trade_table:
        if not isinstance(trade, dict):
            continue
        side = str(trade.get("side", "")).lower()
        if side == "buy":
            buy_count += 1
        elif side == "sell":
            sell_count += 1
        if trade.get("timestamp"):
            timestamps.append(trade["timestamp"])

    return {
        "trade_count": int(metrics.get("trade_count") or len(trade_table)),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "win_rate": metrics.get("win_rate", 0),
        "average_win": metrics.get("average_win", 0),
        "average_loss": metrics.get("average_loss", 0),
        "profit_loss_ratio": metrics.get("profit_loss_ratio", 0),
        "first_trade_at": timestamps[0] if timestamps else None,
        "last_trade_at": timestamps[-1] if timestamps else None,
    }


def build_immutable_payload(backtest: BacktestRun, title: str, publisher: User, session: SessionDep) -> dict:
    report_metadata = build_report_metadata(backtest, title, publisher)
    payload = {
        "title": title,
        "strategy_id": backtest.strategy_id,
        "strategy_version": "0.1.0",
        "parameter_set_id": backtest.parameter_set_id,
        "backtest_run_id": backtest.id,
        "backtest_config": backtest.config,
        "report_metadata": report_metadata,
        "report_summary": build_report_summary(backtest),
        "data_summary": build_data_summary(backtest),
        "risk_metrics": build_risk_metrics(backtest),
        "trade_summary": build_trade_summary(backtest),
        "assumptions": build_report_assumptions(backtest),
        "data_quality": build_data_quality_summary(backtest),
        "metrics": backtest.metrics,
        "technical_indicators": backtest.result_payload.get("technical_indicators", {}),
        "indicator_summary": backtest.result_payload.get("indicator_summary", {}),
        "signal_summary": backtest.result_payload.get("signal_summary", {}),
        "result_payload": backtest.result_payload,
        "generated_at": report_metadata["generated_at"],
        "publisher": publisher.username,
        "risk_disclosure": backtest.result_payload.get(
            "risk_disclosure",
            "Backtest results are simulated and do not represent real-money trading.",
        ),
    }
    narrative = get_current_narrative_for_backtest(session, backtest.id)
    if narrative and narrative.status == "reviewed" and narrative.reviewed_payload:
        payload["narrative"] = build_public_narrative_payload(narrative)
    return payload


@router.get("/snapshots", response_model=list[SnapshotResponse])
def list_snapshots(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> list[SnapshotResponse]:
    statement = select(PublishedSnapshot).order_by(PublishedSnapshot.created_at.desc())
    return [snapshot_response(snapshot) for snapshot in session.exec(statement).all()]


@router.post("/snapshots/publish", response_model=SnapshotPublishResponse)
def publish_snapshot(
    payload: SnapshotPublishRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> SnapshotPublishResponse:
    backtest = session.get(BacktestRun, payload.backtest_run_id)
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown backtest id: {payload.backtest_run_id}",
        )
    if backtest.status != TaskStatus.succeeded:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only succeeded backtests can be published")

    prior_statement = select(PublishedSnapshot).where(PublishedSnapshot.backtest_run_id == backtest.id)
    prior_versions = [snapshot.version for snapshot in session.exec(prior_statement).all()]
    version = max(prior_versions, default=0) + 1

    snapshot = PublishedSnapshot(
        backtest_run_id=backtest.id or 0,
        version=version,
        status=SnapshotStatus.published,
        title=payload.title.strip(),
        immutable_payload=build_immutable_payload(backtest, payload.title.strip(), current_user, session),
        published_at=utc_now(),
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)

    share_link, share_token = create_share_link_for_snapshot(snapshot)
    session.add(share_link)
    session.commit()

    record_operation(
        session,
        action="snapshot.publish",
        actor=current_user.username,
        target_type="published_snapshot",
        target_id=str(snapshot.id),
        detail={"backtest_run_id": backtest.id, "version": version},
    )
    if snapshot.immutable_payload.get("narrative"):
        record_operation(
            session,
            action="narrative.publish.included",
            actor=current_user.username,
            target_type="published_snapshot",
            target_id=str(snapshot.id),
            detail={"backtest_run_id": backtest.id, "version": version},
        )
    return SnapshotPublishResponse(snapshot=snapshot_response(snapshot), share_token=share_token)


@router.get("/share-links", response_model=list[ShareLinkResponse])
def list_share_links(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> list[ShareLinkResponse]:
    statement = select(ShareLink).order_by(ShareLink.created_at.desc())
    responses: list[ShareLinkResponse] = []
    for share_link in session.exec(statement).all():
        snapshot = session.get(PublishedSnapshot, share_link.snapshot_id)
        if snapshot:
            responses.append(share_link_response(share_link, snapshot))
    return responses


@router.post("/snapshots/{snapshot_id}/share-links", response_model=ShareLinkCreateResponse)
def create_snapshot_share_link(
    snapshot_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> ShareLinkCreateResponse:
    snapshot = session.get(PublishedSnapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    if snapshot.status != SnapshotStatus.published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only published snapshots can create links")

    share_link, share_token = create_share_link_for_snapshot(snapshot)
    session.add(share_link)
    session.commit()
    session.refresh(share_link)

    record_operation(
        session,
        action="share_link.create",
        actor=current_user.username,
        target_type="share_link",
        target_id=str(share_link.id),
        detail={"snapshot_id": snapshot.id},
    )
    return ShareLinkCreateResponse(share_link=share_link_response(share_link, snapshot), share_token=share_token)


@router.post("/share-links/{share_link_id}/revoke", response_model=ShareLinkResponse)
def revoke_share_link(
    share_link_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> ShareLinkResponse:
    share_link = session.get(ShareLink, share_link_id)
    if not share_link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    snapshot = session.get(PublishedSnapshot, share_link.snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    share_link.is_active = False
    session.add(share_link)
    session.commit()
    session.refresh(share_link)

    record_operation(
        session,
        action="share_link.revoke",
        actor=current_user.username,
        target_type="share_link",
        target_id=str(share_link.id),
        detail={"snapshot_id": snapshot.id},
    )
    return share_link_response(share_link, snapshot)


@router.post("/snapshots/{snapshot_id}/revoke", response_model=SnapshotResponse)
def revoke_snapshot(
    snapshot_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> SnapshotResponse:
    snapshot = session.get(PublishedSnapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    snapshot.status = SnapshotStatus.revoked
    session.add(snapshot)
    statement = select(ShareLink).where(ShareLink.snapshot_id == snapshot_id)
    for share_link in session.exec(statement).all():
        share_link.is_active = False
        session.add(share_link)
    session.commit()
    session.refresh(snapshot)

    record_operation(
        session,
        action="snapshot.revoke",
        actor=current_user.username,
        target_type="published_snapshot",
        target_id=str(snapshot.id),
        detail={},
    )
    return snapshot_response(snapshot)


@router.get("/public/snapshots/{share_token}", response_model=PublicSnapshotResponse)
def get_public_snapshot(share_token: str, session: SessionDep) -> PublicSnapshotResponse:
    token_hash = hash_share_token(share_token)
    share_link = session.exec(
        select(ShareLink).where(ShareLink.token_hash == token_hash, ShareLink.is_active == True)  # noqa: E712
    ).first()
    if not share_link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    snapshot = session.get(PublishedSnapshot, share_link.snapshot_id)
    if not snapshot or snapshot.status != SnapshotStatus.published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    return PublicSnapshotResponse(
        id=snapshot.id or 0,
        title=snapshot.title,
        version=snapshot.version,
        payload=snapshot.immutable_payload,
        published_at=snapshot.published_at,
    )
