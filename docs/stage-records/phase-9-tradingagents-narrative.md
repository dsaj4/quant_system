# Phase 9 - TradingAgents Client Narrative

Date: 2026-06-03

## Goal

Add a reviewed, explainable, and auditable research narrative layer to the existing quantitative report flow without changing strategy signals, backtest metrics, paper trading behavior, or immutable snapshot semantics.

## Completed

- Added `NarrativeRun` persistence and Alembic migration.
- Added conservative quant rating service: `positive`, `neutral`, `cautious`.
- Added A-share ticker mapping for external providers: `SH/SSE -> .SS`, `SZ/SZSE -> .SZ`.
- Added narrative input summaries for single instruments and portfolio top-weight coverage.
- Added TradingAgents provider abstraction, mock provider, and real TradingAgents lazy import provider.
- Added a narrative state machine: `pending`, `running`, `succeeded`, `degraded`, `failed`, `reviewed`.
- Added service-level provider timeout handling so stalled TradingAgents calls resolve to `failed` and release the running lock.
- Added authenticated admin Narrative API for config, generate, fetch current run, edit draft, acknowledge degraded output, approve, withdraw review, and regenerate.
- Included reviewed narrative payloads in published snapshots only when a reviewed narrative exists at publish time.
- Kept public snapshot payloads limited to client-safe narrative fields.
- Added an admin review workspace for AI research narratives.
- Added client display rendering after charts and before trade records.
- Added TradingAgents smoke script and runbook.

## Safety Boundaries

- Client display does not show the TradingAgents name.
- Client display does not show raw provider suggestions.
- Client display does not show degraded status or degraded reasons.
- Client display does not show reviewer identity, review time, analysis date, or quant rating internals.
- TradingAgents is only a narrative provider. It does not rewrite quant results.
- Published snapshots are immutable and are not changed by later narrative regeneration.

## Verification

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v
```

Result: `96 passed`.

Admin frontend:

```powershell
cd frontend-admin
npm.cmd run build
```

Result: passed. Vite reported only the existing chunk size warning.

Client display frontend:

```powershell
cd frontend-display
npm.cmd run build
```

Result: passed. Vite reported only the existing chunk size warning.

Browser baseline checks:

- Admin dev server at `http://127.0.0.1:5183` returned 200 and rendered the login page.
- Client display dev server at `http://127.0.0.1:5184` returned 200 and rendered the expected missing-token report state.

Real TradingAgents smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_tradingagents_smoke.ps1 -ApiBase "http://127.0.0.1:8000/api"
```

Observed result with `QUANT_TRADING_AGENTS_TIMEOUT_SECONDS=60`:

- Backend health: ok.
- Provider config: DeepSeek configured.
- Smoke backtest: succeeded.
- Narrative generation accepted.
- Narrative run moved from `running` to `failed` on poll 6.
- Error message: `TradingAgents narrative provider timed out after 60 seconds`.

This confirms the integration path is reachable and the timeout guard prevents permanent `running` state. It does not yet confirm that the real TradingAgents provider can produce an acceptable draft within the available external API/network window.

## Remaining Work

- Re-run the real smoke with a longer timeout once external API latency and quota are acceptable.
- If the real provider still times out, profile TradingAgents analyst selection, data vendor calls, and DeepSeek response latency.
- Tune the module normalization rules after reviewing the first successful real TradingAgents draft.
- Publish only explicitly marked smoke/test snapshots during validation.
