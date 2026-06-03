# TradingAgents Smoke Runbook

This runbook verifies the real TradingAgents narrative provider path for the client research narrative feature.

## Required Local Configuration

Keep secrets in `.env` or the process environment. Do not commit them.

Required:

```env
QUANT_TRADING_AGENTS_ENABLED=true
QUANT_TRADING_AGENTS_LLM_PROVIDER=deepseek
QUANT_TRADING_AGENTS_DEEP_THINK_LLM=deepseek-reasoner
QUANT_TRADING_AGENTS_QUICK_THINK_LLM=deepseek-chat
QUANT_TRADING_AGENTS_OUTPUT_LANGUAGE=Chinese
QUANT_TRADING_AGENTS_DATA_VENDOR=yfinance
DEEPSEEK_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
```

Optional:

```env
QUANT_TRADING_AGENTS_RESULTS_DIR=./data/tradingagents/logs
QUANT_TRADING_AGENTS_CACHE_DIR=./data/tradingagents/cache
QUANT_TRADING_AGENTS_MEMORY_LOG_PATH=./data/tradingagents/memory/trading_memory.md
QUANT_TRADING_AGENTS_NEWS_ARTICLE_LIMIT=10
QUANT_TRADING_AGENTS_GLOBAL_NEWS_ARTICLE_LIMIT=5
```

## Install

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The backend lazy-imports TradingAgents, so the app can still start if the package is absent. The real smoke test requires `tradingagents==0.2.5`.

## Start Backend

Use the normal local startup flow:

```powershell
.\start_quant_local.ps1
```

Or start the backend with the README command if running services separately.

## Run Smoke

```powershell
.\scripts\run_tradingagents_smoke.ps1
```

The script:

- logs in as `admin`
- verifies `/api/narratives/config`
- creates or reuses `600519.SH`
- creates a small succeeded backtest
- starts a narrative generation with `is_smoke_test=true`
- maps `600519.SH` to `600519.SS`
- polls until the saved `NarrativeRun` is `succeeded`, `degraded`, or `failed`

Expected acceptable outcomes:

- `succeeded`: can enter review directly
- `degraded`: can enter review after admin acknowledgement

Failure outcome:

- `failed`: inspect `error_message`, backend logs, provider keys, and external data/API availability

## Publishing A Test Snapshot

After a smoke run succeeds or degrades acceptably:

1. Open the admin publication workspace.
2. Review the smoke/test narrative.
3. Publish a snapshot with a title clearly marking test nature, such as `TradingAgents Smoke Test - 600519`.

The client display must not expose TradingAgents name, raw provider suggestion, degraded reasons, reviewer identity, review timestamp, analysis date, or quant rating internals.

## Notes

- TradingAgents is used only as a narrative provider. It must not change backtest metrics, strategy signals, simulated trades, or live trading behavior.
- The customer-facing rating remains aligned to the quant rating. Raw provider suggestions are kept only in the admin/audit surface.
- A published snapshot is immutable. Regenerating or editing a later narrative must not alter an existing public link.
