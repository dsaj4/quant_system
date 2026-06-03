from dataclasses import dataclass
from enum import Enum
import os
from typing import Any, Protocol

from app.core.config import PROJECT_ROOT, Settings
from app.services.narrative_rating import QuantRating


CLIENT_NARRATIVE_LABEL = "AI 投研参考结论"
CLIENT_NARRATIVE_DISCLAIMER = "AI 辅助生成，已人工审核。本区块用于解释量化结果，不构成投资建议。"


class ProviderRunStatus(str, Enum):
    succeeded = "succeeded"
    degraded = "degraded"
    failed = "failed"


@dataclass(frozen=True)
class ProviderResult:
    status: ProviderRunStatus
    structured_summary: dict[str, Any]
    raw_suggestion: str
    degraded_reasons: list[str]
    provider_model: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class NormalizedProviderResult:
    client_payload: dict[str, Any]
    provider_structured_summary: dict[str, Any]
    provider_raw_suggestion: str
    provider_conflict: bool
    degraded_reasons: list[str]
    provider_model: str


class NarrativeProvider(Protocol):
    def is_configured(self) -> bool:
        ...

    def run(self, input_summary: dict[str, Any]) -> ProviderResult:
        ...


class MockNarrativeProvider:
    def __init__(
        self,
        *,
        status: ProviderRunStatus = ProviderRunStatus.succeeded,
        structured_summary: dict[str, Any] | None = None,
        raw_suggestion: str = "Hold",
        degraded_reasons: list[str] | None = None,
        error_message: str = "",
        provider_model: str = "mock",
    ) -> None:
        self.status = status
        self.structured_summary = structured_summary or {}
        self.raw_suggestion = raw_suggestion
        self.degraded_reasons = degraded_reasons or []
        self.error_message = error_message
        self.provider_model = provider_model

    def is_configured(self) -> bool:
        return True

    def run(self, input_summary: dict[str, Any]) -> ProviderResult:
        if self.status == ProviderRunStatus.failed:
            raise RuntimeError(self.error_message or "Narrative provider failed")
        return ProviderResult(
            status=self.status,
            structured_summary=self.structured_summary,
            raw_suggestion=self.raw_suggestion,
            degraded_reasons=self.degraded_reasons,
            provider_model=self.provider_model,
        )


class TradingAgentsNarrativeProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(
            self.settings.trading_agents_enabled
            and self.settings.trading_agents_llm_provider
            and self.settings.trading_agents_deep_think_llm
            and self.settings.trading_agents_quick_think_llm
        )

    def selected_analysts(self) -> list[str]:
        analysts = [
            analyst.strip()
            for analyst in (self.settings.trading_agents_selected_analysts or "").split(",")
            if analyst.strip()
        ]
        return analysts or ["market", "social", "news", "fundamentals"]

    def _config(self) -> dict[str, Any]:
        data_vendor = self.settings.trading_agents_data_vendor or "yfinance"
        return {
            "llm_provider": self.settings.trading_agents_llm_provider,
            "deep_think_llm": self.settings.trading_agents_deep_think_llm,
            "quick_think_llm": self.settings.trading_agents_quick_think_llm,
            "output_language": self.settings.trading_agents_output_language,
            "max_debate_rounds": self.settings.trading_agents_max_debate_rounds,
            "max_risk_discuss_rounds": self.settings.trading_agents_max_risk_rounds,
            "checkpoint_enabled": self.settings.trading_agents_checkpoint_enabled,
            "results_dir": self.settings.trading_agents_results_dir,
            "data_cache_dir": self.settings.trading_agents_cache_dir,
            "memory_log_path": self.settings.trading_agents_memory_log_path,
            "news_article_limit": self.settings.trading_agents_news_article_limit,
            "global_news_article_limit": self.settings.trading_agents_global_news_article_limit,
            "data_vendors": {
                "core_stock_apis": data_vendor,
                "technical_indicators": data_vendor,
                "fundamental_data": data_vendor,
                "news_data": data_vendor,
            },
        }

    def _load_env_keys(self) -> None:
        for env_path in (PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"):
            if not env_path.exists():
                continue
            for line in env_path.read_text(encoding="utf-8-sig").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                key = key.strip()
                if key.startswith("QUANT_") or key in os.environ:
                    continue
                os.environ[key] = value.strip().strip('"').strip("'")

    def run(self, input_summary: dict[str, Any]) -> ProviderResult:
        if not self.is_configured():
            raise RuntimeError("TradingAgents narrative provider is not configured")

        self._load_env_keys()
        try:
            from tradingagents.default_config import DEFAULT_CONFIG
            from tradingagents.graph.trading_graph import TradingAgentsGraph
        except ImportError as exc:
            raise RuntimeError("TradingAgents package is not installed") from exc

        targets = input_summary.get("targets") or []
        if not targets:
            raise RuntimeError("TradingAgents narrative input has no targets")

        first_target = targets[0]
        ticker = first_target.get("tradingagents_ticker")
        analysis_date = input_summary.get("analysis_date")
        if not ticker or not analysis_date:
            raise RuntimeError("TradingAgents narrative input requires ticker and analysis date")

        config = DEFAULT_CONFIG.copy()
        config.update(self._config())
        graph = TradingAgentsGraph(selected_analysts=self.selected_analysts(), debug=False, config=config)
        final_state, decision = graph.propagate(ticker, analysis_date)

        return ProviderResult(
            status=ProviderRunStatus.succeeded,
            structured_summary={
                "technical": final_state.get("market_report", ""),
                "market_news": final_state.get("news_report", ""),
                "fundamentals": final_state.get("fundamentals_report", ""),
                "sentiment": final_state.get("sentiment_report", ""),
                "investment_plan": final_state.get("investment_plan", ""),
                "trader_investment_plan": final_state.get("trader_investment_plan", ""),
                "final_trade_decision": final_state.get("final_trade_decision", ""),
            },
            raw_suggestion=str(decision),
            degraded_reasons=[],
            provider_model=self.settings.trading_agents_deep_think_llm,
        )


MODULE_DEFINITIONS = [
    ("one_liner", "一句话结论", True),
    ("selection_logic", "选股/组合逻辑", True),
    ("quant_performance", "量化表现解读", True),
    ("technical_context", "技术面解释", False),
    ("fundamental_context", "基本面/业务背景摘要", False),
    ("market_news_context", "市场资讯背景摘要", False),
    ("counterpoints_risks", "反方观点与风险情景", True),
    ("boundaries_disclaimer", "适用边界与免责声明", False),
]


SUMMARY_KEYS = {
    "one_liner": ("one_liner", "summary"),
    "selection_logic": ("selection_logic", "investment_plan"),
    "quant_performance": ("quant_performance", "strategy_context"),
    "technical_context": ("technical_context", "technical", "market_report"),
    "fundamental_context": ("fundamental_context", "fundamentals"),
    "market_news_context": ("market_news_context", "market_news", "news", "sentiment"),
    "counterpoints_risks": ("counterpoints_risks", "risks", "risk", "final_trade_decision"),
    "boundaries_disclaimer": ("boundaries_disclaimer", "disclaimer"),
}


def _string_summary(structured_summary: dict[str, Any], module_key: str, fallback: str) -> str:
    for key in SUMMARY_KEYS[module_key]:
        value = structured_summary.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _provider_suggestion_rating(raw_suggestion: str) -> QuantRating:
    normalized = raw_suggestion.strip().lower()
    if normalized in {"buy", "overweight", "positive"}:
        return QuantRating.positive
    if normalized in {"sell", "underweight", "cautious"}:
        return QuantRating.cautious
    return QuantRating.neutral


def _fallback_summary(module_key: str, quant_rating: QuantRating, input_summary: dict[str, Any]) -> str:
    scope_label = "组合" if input_summary.get("target_scope") == "portfolio" else "标的"
    fallbacks = {
        "one_liner": f"本区块用于解释当前{scope_label}的量化结果，评级为 {quant_rating.value}。",
        "selection_logic": f"当前说明基于已完成回测与选定{scope_label}，不新增独立选股信号。",
        "quant_performance": "量化表现以回测收益、回撤、交易次数和数据质量为主要解释基础。",
        "technical_context": "技术面信息用于辅助解释量化结果，不改变策略信号。",
        "fundamental_context": "基本面信息仅作为背景说明，第一版不作为量化评级输入。",
        "market_news_context": "市场资讯用于解释环境变化，可能存在外部数据覆盖不完整。",
        "counterpoints_risks": "若样本较短、回撤扩大或外部数据不足，应降低结论强度。",
        "boundaries_disclaimer": "本区块用于解释既有量化结果，不构成投资建议。",
    }
    return fallbacks[module_key]


def _module_payload(
    *,
    key: str,
    title: str,
    default_expanded: bool,
    structured_summary: dict[str, Any],
    quant_rating: QuantRating,
    input_summary: dict[str, Any],
) -> dict[str, Any]:
    summary = _string_summary(structured_summary, key, _fallback_summary(key, quant_rating, input_summary))
    return {
        "key": key,
        "title": title,
        "summary": summary,
        "paragraphs": [summary],
        "bullets": [],
        "visible": True,
        "default_expanded": default_expanded,
    }


def normalize_provider_result(
    provider_result: ProviderResult,
    *,
    quant_rating: QuantRating,
    input_summary: dict[str, Any],
) -> NormalizedProviderResult:
    provider_rating = _provider_suggestion_rating(provider_result.raw_suggestion)
    provider_conflict = provider_rating != QuantRating.neutral and provider_rating != quant_rating
    modules = [
        _module_payload(
            key=key,
            title=title,
            default_expanded=default_expanded,
            structured_summary=provider_result.structured_summary,
            quant_rating=quant_rating,
            input_summary=input_summary,
        )
        for key, title, default_expanded in MODULE_DEFINITIONS
    ]

    return NormalizedProviderResult(
        client_payload={
            "enabled": True,
            "label": CLIENT_NARRATIVE_LABEL,
            "rating": quant_rating.value,
            "reviewed": False,
            "disclaimer": CLIENT_NARRATIVE_DISCLAIMER,
            "modules": modules,
        },
        provider_structured_summary=provider_result.structured_summary,
        provider_raw_suggestion=provider_result.raw_suggestion,
        provider_conflict=provider_conflict,
        degraded_reasons=provider_result.degraded_reasons,
        provider_model=provider_result.provider_model,
    )
