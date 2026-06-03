import pytest

from app.core.config import Settings
from app.services.narrative_provider import (
    MockNarrativeProvider,
    ProviderRunStatus,
    TradingAgentsNarrativeProvider,
    normalize_provider_result,
)
from app.services.narrative_rating import QuantRating


def test_missing_provider_config_reports_disabled() -> None:
    provider = TradingAgentsNarrativeProvider(
        Settings(
            trading_agents_enabled=False,
            trading_agents_llm_provider="",
            trading_agents_deep_think_llm="",
            trading_agents_quick_think_llm="",
        )
    )

    assert provider.is_configured() is False


def test_mock_provider_returns_succeeded_structured_output() -> None:
    provider = MockNarrativeProvider(
        status=ProviderRunStatus.succeeded,
        raw_suggestion="Buy",
        structured_summary={"technical": "趋势保持向上。"},
    )

    result = provider.run({"targets": [{"tradingagents_ticker": "600519.SS"}]})

    assert result.status == ProviderRunStatus.succeeded
    assert result.structured_summary["technical"] == "趋势保持向上。"
    assert result.raw_suggestion == "Buy"
    assert result.degraded_reasons == []


def test_mock_provider_can_return_degraded_output_with_reasons() -> None:
    provider = MockNarrativeProvider(
        status=ProviderRunStatus.degraded,
        degraded_reasons=["news source unavailable"],
    )

    result = provider.run({})

    assert result.status == ProviderRunStatus.degraded
    assert result.degraded_reasons == ["news source unavailable"]


def test_mock_provider_can_fail_with_clear_error() -> None:
    provider = MockNarrativeProvider(status=ProviderRunStatus.failed, error_message="TradingAgents failed")

    with pytest.raises(RuntimeError, match="TradingAgents failed"):
        provider.run({})


def test_normalization_preserves_raw_suggestion_and_aligns_client_rating_to_quant_rating() -> None:
    provider = MockNarrativeProvider(
        status=ProviderRunStatus.succeeded,
        raw_suggestion="Buy",
        structured_summary={
            "one_liner": "模型倾向积极，但量化评级需要保持审慎。",
            "technical": "价格仍在均线附近震荡。",
            "fundamentals": "业务背景稳定。",
            "news": "近期资讯未见重大负面。",
            "risks": "回撤扩大时需降低解释强度。",
        },
    )
    provider_result = provider.run({})

    normalized = normalize_provider_result(
        provider_result,
        quant_rating=QuantRating.cautious,
        input_summary={"target_scope": "instrument"},
    )

    assert normalized.provider_raw_suggestion == "Buy"
    assert normalized.provider_conflict is True
    assert normalized.client_payload["rating"] == "cautious"
    assert normalized.client_payload["label"] == "AI 投研参考结论"
    assert normalized.client_payload["reviewed"] is False
    assert len(normalized.client_payload["modules"]) == 8
    assert {module["key"] for module in normalized.client_payload["modules"]} == {
        "one_liner",
        "selection_logic",
        "quant_performance",
        "technical_context",
        "fundamental_context",
        "market_news_context",
        "counterpoints_risks",
        "boundaries_disclaimer",
    }
    assert normalized.client_payload["modules"][0]["visible"] is True
    assert normalized.client_payload["modules"][0]["default_expanded"] is True


def test_normalization_defaults_all_modules_when_provider_is_sparse() -> None:
    provider = MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Hold")
    normalized = normalize_provider_result(
        provider.run({}),
        quant_rating=QuantRating.neutral,
        input_summary={"target_scope": "portfolio"},
    )

    modules = {module["key"]: module for module in normalized.client_payload["modules"]}
    assert modules["technical_context"]["default_expanded"] is False
    assert modules["fundamental_context"]["visible"] is True
    assert modules["boundaries_disclaimer"]["summary"]
