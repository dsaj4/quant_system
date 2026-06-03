# TradingAgents Client Narrative Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an AI-assisted, human-reviewed, snapshot-bound investment research narrative layer to the existing client report, using TradingAgents as the first provider while preserving the current quant report and immutable snapshot flow.

**Architecture:** The feature adds an internal narrative run/review workflow beside existing backtest and snapshot publishing. TradingAgents runs asynchronously as an application-level background task, stores internal draft/audit data in backend tables, and publishes only the reviewed final structured narrative into `PublishedSnapshot.immutable_payload`. The client display renders the reviewed final narrative after charts and before trade records, without exposing raw AI drafts, TradingAgents name, degraded status, reviewer identity, analysis date, or rating rule details.

**Tech Stack:** FastAPI, SQLModel, SQLite/Alembic, APScheduler-adjacent application runtime, React/Vite/TypeScript, ECharts, pytest, mocked provider tests, real TradingAgents smoke test for `600519.SH -> 600519.SS`.

---

## 0. Decisions Already Aligned

- Enhance the existing published snapshot report; do not build a separate research page.
- Narrative is generated before publishing, manually reviewed, then frozen into the snapshot.
- Narrative binds to one backtest/snapshot context, not to a reusable instrument profile.
- Snapshot may still be published without narrative.
- If a reviewed narrative exists, publish defaults to including it and clearly prompts the admin.
- Public snapshot payload contains only the reviewed final narrative, never raw AI draft or provider internals.
- First version depends on TradingAgents being configured. If not configured, narrative generation is disabled.
- TradingAgents is used only as a narrative provider. It must not alter backtest metrics, strategy signals, simulated trades, or real trading behavior.
- TradingAgents final suggestion must not conflict with the quant rating shown to clients. Preserve raw provider suggestion internally; align client-facing AI research reference conclusion to quant rating.
- The client label is `AI 投研参考结论`.
- Client side says only `AI 辅助生成，已人工审核。本区块用于解释量化结果，不构成投资建议。`
- Client side does not show TradingAgents name, degraded status, reviewer, review time, analysis date, or rating rule details.
- Admin side shows structured provider summaries, raw final provider suggestion, conflict status, degraded status/reasons, draft/final payload, and collapsed generation input summary.
- Narrative modules are structured fields, not Markdown or HTML.
- Modules are Chinese only, professional, restrained, explanatory, and non-marketing.
- Eight modules are supported:
  - `one_liner`: 一句话结论
  - `selection_logic`: 选股/组合逻辑
  - `quant_performance`: 量化表现解读
  - `technical_context`: 技术面解释
  - `fundamental_context`: 基本面/业务背景摘要
  - `market_news_context`: 市场资讯背景摘要
  - `counterpoints_risks`: 反方观点与风险情景
  - `boundaries_disclaimer`: 适用边界与免责声明
- Default visible/expanded on client:
  - Visible and expanded: one-liner, selection logic, quant performance, counterpoints/risks.
  - Visible but collapsed by default unless admin changes it: technical, fundamental, market news, boundaries.
  - Admin can hide each module individually.
- Client report order:
  - hero
  - metric strip
  - charts
  - narrative
  - trade records
  - assumptions
  - risk disclosure
- Narrative length limits:
  - one-liner max 80 Chinese characters
  - module summary max 120 Chinese characters
  - module paragraphs max 3, each max 180 Chinese characters
  - bullets max 5, each max 80 Chinese characters
  - over-limit drafts can be saved but cannot be reviewed.
- Generate only from succeeded backtests.
- Data quality warnings do not block generation; they must influence the conservative rating and risk wording.
- Quant rating is fixed-rule, conservative, backend-defined constants, no UI config.
- Admin cannot change quant rating in first version.
- Customer sees only the rating, not rating rationale.
- Re-generate is allowed before publish; only latest draft/final is retained. Operation logs record regeneration.
- Reviewed narrative cannot be edited unless review is withdrawn.
- Reviewed narrative does not expire; admin sees generation/review timestamps.
- Same backtest can publish multiple snapshot versions with different narrative payloads.
- Regenerating narrative never changes already-published snapshots.
- Application allows only one global TradingAgents narrative task at a time. New generation requests are rejected while another is running.
- No cancel support in first version.
- TradingAgents config comes from `.env` / `QUANT_` environment variables, not UI.
- Partial provider/data-source failure is `degraded`; admin must explicitly acknowledge degraded state before review can be approved. Client does not show degraded state.
- Combination/portfolio reports analyze Top 3 weighted instruments separately and summarize; admin sees coverage, client does not explicitly list coverage limits.
- Ticker mapping first version:
  - SH/SSE -> `.SS`
  - SZ/SZSE -> `.SZ`
  - unmappable instrument cannot generate narrative.
- Admin can choose AI analysis date.
  - It cannot be later than current date.
  - It may be earlier than backtest end date, but admin gets warning and internal audit records it.
- No client-side FAQ/free Q&A in first version.
- Backend automated tests mock TradingAgents.
- Acceptance includes one real TradingAgents smoke run for `600519.SH`, mapped to `600519.SS`, saved as a normal narrative run marked `smoke/test`, and allowed to publish with test marking in admin/title.

---

## 1. Codebase Reference

Read these files before implementation:

- `README.md`: current app capabilities and local run commands.
- `backend/app/models/core.py`: existing SQLModel entities.
- `backend/app/api/router.py`: API router registration.
- `backend/app/api/backtests.py`: succeeded backtest contract and result payload shape.
- `backend/app/api/snapshots.py`: snapshot publishing, immutable payload construction, public token endpoint.
- `backend/app/api/paper_runs.py`: existing status-history style for simulated runs.
- `backend/app/services/backtest.py`: metrics/result payload fields used for rating and narrative inputs.
- `backend/app/services/operation_log.py`: audit logging helper.
- `backend/app/core/config.py`: settings pattern and `QUANT_` env prefix.
- `backend/app/services/schema.py` and `alembic/versions/*`: migration/schema repair pattern.
- `frontend-admin/src/api/client.ts`: admin API client types and request helpers.
- `frontend-admin/src/App.tsx`: current admin orchestration.
- `frontend-admin/src/sections/PublicationSection.tsx`: snapshot publishing UI.
- `frontend-display/src/App.tsx`: public report rendering order and payload types.
- `frontend-display/src/App.css`: public report layout styles.
- `backend/tests/test_snapshots.py`: public snapshot immutability and token behavior.
- `backend/tests/test_paper_runs.py`: status flow and operation log expectations.

---

## 2. Data Contracts

### Internal NarrativeRun

Create an internal SQLModel table. Suggested fields:

- `id`
- `backtest_run_id`
- `status`: `draft | pending | running | succeeded | degraded | failed | reviewed`
- `is_smoke_test`: bool
- `provider`: default `trading_agents`
- `provider_model`: string
- `analysis_date`: date string
- `quant_rating`: `positive | neutral | cautious`
- `quant_rating_inputs`: JSON, internal only
- `target_scope`: `instrument | portfolio`
- `target_summary`: JSON
- `ticker_mapping`: JSON
- `coverage_summary`: JSON
- `input_summary`: JSON
- `provider_structured_summary`: JSON
- `provider_raw_suggestion`: string
- `provider_conflict`: bool
- `degraded_reasons`: JSON list
- `degraded_acknowledged_by`
- `degraded_acknowledged_at`
- `ai_draft_payload`: JSON
- `reviewed_payload`: JSON
- `reviewed_by`
- `reviewed_at`
- `review_note`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

Only one current narrative run per `backtest_run_id` should exist in first version. Enforce this in service logic, not necessarily by destructive migration until implementation chooses the cleanest approach.

### Public Snapshot Narrative Payload

Only this final structure may be copied into `PublishedSnapshot.immutable_payload`:

```json
{
  "narrative": {
    "enabled": true,
    "label": "AI 投研参考结论",
    "rating": "neutral",
    "reviewed": true,
    "disclaimer": "AI 辅助生成，已人工审核。本区块用于解释量化结果，不构成投资建议。",
    "modules": [
      {
        "key": "quant_performance",
        "title": "量化表现解读",
        "summary": "...",
        "paragraphs": ["..."],
        "bullets": ["..."],
        "visible": true,
        "default_expanded": true
      }
    ]
  }
}
```

Do not include:

- `ai_draft_payload`
- TradingAgents name
- raw provider suggestion
- provider logs
- degraded status or reasons
- reviewer identity/time
- analysis date
- quant rating inputs/rule details

---

## 3. Task List

### Task 1: Add Narrative Models and Migration

**Files:**

- Modify: `backend/app/models/core.py`
- Modify: `backend/app/services/schema.py`
- Create: `alembic/versions/20260603_000003_narrative_runs.py`
- Test: `backend/tests/test_narrative_models.py`

**Step 1: Write failing model/migration tests**

Add tests that assert:

- `narrativerun` table exists.
- Required columns exist.
- JSON columns round-trip draft/final payloads.
- Status enum values include `pending`, `running`, `succeeded`, `degraded`, `failed`, `reviewed`.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_models.py -v
```

Expected: FAIL because model/table does not exist.

**Step 2: Add model**

Add `NarrativeStatus` enum and `NarrativeRun` model to `backend/app/models/core.py`.

Use JSON columns for provider summary, draft, final, input summary, and rating inputs.

**Step 3: Add migration and SQLite repair**

Create Alembic revision for the new table.

Update `backend/app/services/schema.py` only if current project pattern requires dev SQLite compatibility for new tables/columns.

**Step 4: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_models.py backend\tests\test_migrations.py backend\tests\test_schema_health.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add backend/app/models/core.py backend/app/services/schema.py alembic/versions/20260603_000003_narrative_runs.py backend/tests/test_narrative_models.py
git commit -m "feat: add narrative run persistence"
```

---

### Task 2: Add Quant Rating Service

**Files:**

- Create: `backend/app/services/narrative_rating.py`
- Test: `backend/tests/test_narrative_rating.py`

**Step 1: Write failing tests**

Cover conservative rating behavior:

- Negative cumulative return -> cautious.
- Severe drawdown -> cautious.
- Sample/data warning caps rating at neutral.
- Positive return plus acceptable drawdown and enough bars -> positive.
- Weak/mixed metrics -> neutral.

Use existing backtest metric keys:

- `cumulative_return`
- `max_drawdown`
- `sharpe_ratio`
- `return_drawdown_ratio`
- `bar_count`
- `trade_count`
- `data_quality.status`
- `data_quality.warnings`

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_rating.py -v
```

Expected: FAIL because service does not exist.

**Step 2: Implement service**

Implement:

- `QuantRating` enum or string literals: `positive`, `neutral`, `cautious`
- constants grouped in one place, no UI config
- `calculate_quant_rating(backtest: BacktestRun) -> RatingResult`

Return internal rationale in `rating_inputs`, but never expose it publicly.

**Step 3: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_rating.py -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add backend/app/services/narrative_rating.py backend/tests/test_narrative_rating.py
git commit -m "feat: add conservative narrative rating"
```

---

### Task 3: Add Ticker Mapping and Narrative Input Builder

**Files:**

- Create: `backend/app/services/narrative_inputs.py`
- Test: `backend/tests/test_narrative_inputs.py`

**Step 1: Write failing tests**

Cover:

- `600519` + `SH` maps to `600519.SS`.
- `600519` + `SSE` maps to `600519.SS`.
- `000001` + `SZ` maps to `000001.SZ`.
- `000001` + `SZSE` maps to `000001.SZ`.
- Unsupported exchange fails clearly.
- Single-instrument backtest input summary includes backtest id, strategy id, period, data quality status, ticker mapping, analysis date.
- Portfolio input summary covers Top 3 weighted instruments.
- Analysis date later than current date rejects.
- Analysis date earlier than backtest end date records warning, not rejection.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_inputs.py -v
```

Expected: FAIL.

**Step 2: Implement input builder**

Implement:

- `map_instrument_to_tradingagents_ticker(instrument)`.
- `build_narrative_input_summary(session, backtest, analysis_date)`.
- `extract_backtest_end_date(backtest.result_payload)`.
- portfolio Top 3 weighted coverage based on `config.positions`.

Do not call TradingAgents here.

**Step 3: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_inputs.py -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add backend/app/services/narrative_inputs.py backend/tests/test_narrative_inputs.py
git commit -m "feat: build narrative generation inputs"
```

---

### Task 4: Add TradingAgents Provider Abstraction and Mockable Provider

**Files:**

- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/narrative_provider.py`
- Test: `backend/tests/test_narrative_provider.py`

**Step 1: Write failing tests**

Cover:

- Missing provider config reports disabled.
- Mock provider can return succeeded structured output.
- Mock provider can return degraded output with reasons.
- Mock provider can fail with clear error.
- Raw provider suggestion is preserved internally.
- Client-aligned draft rating follows quant rating, even when provider suggestion conflicts.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_provider.py -v
```

Expected: FAIL.

**Step 2: Add settings**

Add settings such as:

- `trading_agents_enabled: bool = False`
- `trading_agents_llm_provider: str = ""`
- `trading_agents_model: str = ""`
- provider API key names as needed, but do not expose secrets through APIs

Follow existing `QUANT_` env prefix.

**Step 3: Implement provider interface**

Implement provider result structures:

- `ProviderRunStatus`: `succeeded | degraded | failed`
- `ProviderResult`
- `NarrativeProvider`
- `TradingAgentsNarrativeProvider`
- `MockNarrativeProvider` for tests

The real provider wrapper should be import-lazy so the app can start without TradingAgents installed/configured.

**Step 4: Implement draft normalization**

Provider output must normalize to eight modules with structured pure-text fields and visibility defaults.

Align client-facing rating to quant rating.

Preserve raw provider suggestion in internal fields.

**Step 5: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_provider.py -v
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add backend/app/core/config.py backend/app/services/narrative_provider.py backend/tests/test_narrative_provider.py
git commit -m "feat: add narrative provider abstraction"
```

---

### Task 5: Add Narrative Service and State Machine

**Files:**

- Create: `backend/app/services/narratives.py`
- Test: `backend/tests/test_narrative_service.py`

**Step 1: Write failing tests**

Cover:

- Cannot generate when TradingAgents disabled.
- Cannot generate from missing or non-succeeded backtest.
- Cannot generate when ticker mapping fails.
- Global running task rejects new generation request.
- Generate creates/updates one current run per backtest.
- Status flow: pending -> running -> succeeded.
- Status flow: pending -> running -> degraded.
- Status flow: pending -> running -> failed.
- Degraded run cannot be reviewed until acknowledged.
- Over-limit final payload can be saved but cannot be reviewed.
- Reviewed payload cannot be edited unless review withdrawn.
- Withdraw review returns to draft/editable state.
- Re-generate replaces latest draft/final for that backtest and does not affect published snapshots.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_service.py -v
```

Expected: FAIL.

**Step 2: Implement service**

Implement functions:

- `start_narrative_generation(...)`
- `run_narrative_generation(...)`
- `save_narrative_draft(...)`
- `acknowledge_degraded(...)`
- `approve_narrative_review(...)`
- `withdraw_narrative_review(...)`
- `get_current_narrative_for_backtest(...)`
- `build_public_narrative_payload(...)`

Implement a simple global guard for one running narrative task at a time.

Use operation logs for key transitions.

**Step 3: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_service.py -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add backend/app/services/narratives.py backend/tests/test_narrative_service.py
git commit -m "feat: add narrative review state machine"
```

---

### Task 6: Add Narrative API

**Files:**

- Create: `backend/app/api/narratives.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_narratives_api.py`

**Step 1: Write failing API tests**

Cover authenticated endpoints:

- `GET /api/narratives/config` shows enabled/disabled without leaking secrets.
- `POST /api/narratives/generate` starts async run.
- `GET /api/narratives/backtests/{backtest_id}` returns current narrative run.
- `PATCH /api/narratives/{id}/draft` saves edited structured draft.
- `POST /api/narratives/{id}/acknowledge-degraded`.
- `POST /api/narratives/{id}/approve`.
- `POST /api/narratives/{id}/withdraw-review`.
- `POST /api/narratives/{id}/regenerate`.

Cover unauthenticated rejection.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narratives_api.py -v
```

Expected: FAIL.

**Step 2: Implement API**

Use `BackgroundTasks` or controlled in-app task runner.

Do not expose secrets.

Do not expose raw AI draft through public endpoints. Admin authenticated endpoints may expose internal draft/provider summaries.

**Step 3: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narratives_api.py -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add backend/app/api/narratives.py backend/app/api/router.py backend/tests/test_narratives_api.py
git commit -m "feat: expose narrative admin api"
```

---

### Task 7: Include Reviewed Narrative in Snapshot Publishing

**Files:**

- Modify: `backend/app/api/snapshots.py`
- Test: `backend/tests/test_snapshots.py`
- Test: `backend/tests/test_narrative_snapshot_publish.py`

**Step 1: Write failing tests**

Cover:

- Publishing a snapshot without reviewed narrative still works.
- Publishing a snapshot with reviewed narrative copies final public narrative payload.
- Published payload does not contain AI draft, raw provider suggestion, degraded reasons, reviewer, review time, analysis date, or rating rule inputs.
- Re-generating narrative after publish does not alter old public snapshot.
- Same backtest can publish two snapshots with different narrative payloads.
- Operation log records `narrative.publish.included` when included.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_snapshot_publish.py backend\tests\test_snapshots.py -v
```

Expected: FAIL for narrative-specific behavior.

**Step 2: Modify publish flow**

When building immutable payload, look up reviewed current narrative for the backtest.

If present, include only `build_public_narrative_payload(...)`.

Do not make narrative mandatory.

**Step 3: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_narrative_snapshot_publish.py backend\tests\test_snapshots.py -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add backend/app/api/snapshots.py backend/tests/test_snapshots.py backend/tests/test_narrative_snapshot_publish.py
git commit -m "feat: publish reviewed narrative in snapshots"
```

---

### Task 8: Update Admin API Client Types

**Files:**

- Modify: `frontend-admin/src/api/client.ts`

**Step 1: Add types**

Add TypeScript types for:

- `NarrativeConfig`
- `NarrativeStatus`
- `NarrativeModule`
- `NarrativePayload`
- `NarrativeRun`
- create/generate/update/review request payloads

**Step 2: Add client functions**

Add:

- `fetchNarrativeConfig(token)`
- `generateNarrative(token, input)`
- `fetchNarrativeForBacktest(token, backtestId)`
- `updateNarrativeDraft(token, narrativeId, input)`
- `acknowledgeNarrativeDegraded(token, narrativeId)`
- `approveNarrative(token, narrativeId, input)`
- `withdrawNarrativeReview(token, narrativeId)`
- `regenerateNarrative(token, narrativeId)`

**Step 3: Typecheck**

```powershell
cd frontend-admin
npm.cmd run build
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add frontend-admin/src/api/client.ts
git commit -m "feat: add narrative admin client api"
```

---

### Task 9: Add Admin Narrative Review UI

**Files:**

- Create: `frontend-admin/src/sections/NarrativeSection.tsx`
- Modify: `frontend-admin/src/App.tsx`
- Modify as needed: `frontend-admin/src/App.css`

**Step 1: Add UI section**

Build admin workflow:

- Show TradingAgents configured/enabled status.
- For selected succeeded backtest, show generate button.
- If disabled, disable generation and show `AI 投研未配置`.
- Click generate directly starts generation, no confirmation modal.
- Poll status until succeeded/degraded/failed.
- Show input summary collapsed by default.
- Show structured provider summaries, raw provider suggestion, conflict status, degraded state/reasons.
- For degraded, require explicit acknowledgement before approval.
- Provide module editor for eight modules:
  - title fixed or editable conservatively
  - summary
  - paragraphs
  - bullets
  - visible
  - default expanded
- Allow saving over-limit draft.
- Block approval for over-limit final payload.
- Reviewed state is read-only.
- Allow withdraw review.
- Allow regenerate before publish.
- Show generation/review timestamps in admin only.

**Step 2: Add publish prompt integration**

In publication workflow, when reviewed narrative exists, show a clear line:

`本次发布将包含已审核的 AI 投研叙事，并固化进客户快照。`

Default include it.

**Step 3: Build**

```powershell
cd frontend-admin
npm.cmd run build
```

Expected: PASS.

**Step 4: Manual admin verification**

Run backend and admin frontend. Verify disabled/configured/mocked states as implementation allows.

**Step 5: Commit**

```powershell
git add frontend-admin/src/sections/NarrativeSection.tsx frontend-admin/src/App.tsx frontend-admin/src/App.css
git commit -m "feat: add narrative review workspace"
```

---

### Task 10: Render Narrative on Client Report

**Files:**

- Modify: `frontend-display/src/App.tsx`
- Modify: `frontend-display/src/App.css`

**Step 1: Add payload types**

Add `NarrativePayload` and module types to `SnapshotPayload`.

Ensure legacy/minimal payload without narrative still renders.

**Step 2: Add component**

Create component in `App.tsx` or split if local style prefers:

- `NarrativePanel`
- Shows label `AI 投研参考结论`
- Shows rating only, no rating rationale.
- Shows disclaimer.
- Shows visible modules only.
- Default expanded modules expanded.
- Collapsed modules expandable.
- Does not render hidden modules.
- Does not render provider name, reviewer, review date, analysis date, degraded state, raw AI suggestion.

**Step 3: Place component**

Place after chart panels and before `TradeTable`.

Use current app order carefully:

- keep hero and metric strip unchanged
- keep chart panels before narrative
- move trade table after narrative

**Step 4: Build**

```powershell
cd frontend-display
npm.cmd run build
```

Expected: PASS.

**Step 5: Manual visual verification**

Use Browser plugin or Playwright to inspect desktop and mobile:

- With narrative payload: module appears after charts and before trade records.
- Without narrative payload: report remains normal.
- Text does not overlap or overflow.
- Collapsible modules work.

**Step 6: Commit**

```powershell
git add frontend-display/src/App.tsx frontend-display/src/App.css
git commit -m "feat: render reviewed narrative in client report"
```

---

### Task 11: Add Real TradingAgents Integration

**Files:**

- Modify: `requirements.txt` or `backend/pyproject.toml` if needed
- Modify: `backend/app/services/narrative_provider.py`
- Create: `scripts/run_tradingagents_smoke.ps1`
- Create: `docs/tradingagents-smoke-runbook.md`

**Step 1: Check dependency strategy**

Prefer lazy import and optional install behavior.

Do not break app startup when TradingAgents is absent.

Document required env vars.

**Step 2: Implement real provider wrapper**

Use TradingAgents API shape from its README:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=config)
final_state, decision = ta.propagate("600519.SS", "2026-06-03")
```

Adapt actual version as needed after installing/checking the package. Keep imports inside the provider call.

Extract only:

- technical summary
- market/news summary
- fundamentals/business background summary
- bull/bear or debate summary if available
- risk summary if available
- raw final suggestion
- final decision text

Normalize to eight modules.

**Step 3: Add smoke script**

Script should:

- verify backend env has TradingAgents enabled/configured
- create or use `600519.SH` instrument/backtest as needed
- start narrative generation with `is_smoke_test=true`
- poll until succeeded/degraded/failed
- print narrative run id, status, and whether it can enter review

Do not print secrets.

**Step 4: Manual smoke test**

Run:

```powershell
.\scripts\run_tradingagents_smoke.ps1
```

Expected:

- Generates normal `NarrativeRun` marked smoke/test.
- Uses ticker `600519.SS`.
- Status is `succeeded` or acceptable `degraded`.
- Admin can review it.
- A test snapshot can be published with a title clearly marking test nature.

**Step 5: Commit**

```powershell
git add requirements.txt backend/pyproject.toml backend/app/services/narrative_provider.py scripts/run_tradingagents_smoke.ps1 docs/tradingagents-smoke-runbook.md
git commit -m "feat: integrate tradingagents narrative provider"
```

Only add files that changed. Do not stage both dependency files if only one is used.

---

### Task 12: Full Regression and Acceptance

**Files:**

- Modify: `docs/demo-runbook.md`
- Modify: `docs/demo-checklist.md`
- Create: `docs/stage-records/phase-9-tradingagents-narrative.md`

**Step 1: Run backend tests**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v
```

Expected: PASS.

**Step 2: Run frontend builds**

```powershell
cd frontend-admin
npm.cmd run build
cd ..\frontend-display
npm.cmd run build
cd ..
```

Expected: PASS.

**Step 3: Run manual local app acceptance**

Start services:

```powershell
.\start_quant_local.ps1
```

If existing script behavior is insufficient, use README commands.

Validate:

1. Admin can still login.
2. Existing backtest flow still works.
3. Existing snapshot without narrative still publishes and displays.
4. Narrative generation is disabled when TradingAgents config is absent.
5. With config present, narrative generation starts async.
6. A second generation request while one is running is rejected.
7. Succeeded narrative can be edited and reviewed.
8. Degraded narrative requires explicit admin acknowledgement before review.
9. Reviewed narrative is read-only until withdrawn.
10. Publish prompt says reviewed narrative will be included.
11. Client report shows narrative after charts and before trade records.
12. Client report does not expose raw draft, provider name, degraded state, reviewer/time, analysis date, rating rationale.
13. Re-generating narrative after publish does not affect existing public link.
14. Real TradingAgents smoke test for `600519.SH` has run and saved normal smoke/test narrative run.

**Step 4: Update docs**

Document:

- setup env vars
- disabled state
- generation/review/publish flow
- smoke test process
- customer-side boundaries
- known limitations

**Step 5: Commit**

```powershell
git add docs/demo-runbook.md docs/demo-checklist.md docs/stage-records/phase-9-tradingagents-narrative.md
git commit -m "docs: document tradingagents narrative workflow"
```

---

## 4. Goal Mode Operating Rules

When executing this plan unattended:

- Do tasks sequentially.
- Do not skip tests for a task unless blocked by missing external credentials.
- If TradingAgents credentials are missing, complete mocked/backend/frontend work and stop before real smoke test with a clear blocked report.
- Do not alter existing backtest math, paper run math, strategy registry behavior, or public snapshot token security unless a test requires a narrow compatibility adjustment.
- Do not expose raw AI draft through `/api/public/snapshots/{token}`.
- Do not make narrative mandatory for snapshot publishing.
- Do not show TradingAgents name on the client display.
- Keep client report working with legacy/minimal snapshot payloads.
- Prefer small commits after each task.
- If the worktree has unrelated dirty changes, leave them untouched.

---

## 5. Definition of Done

The feature is complete when:

- Backend tests pass with mocked TradingAgents provider.
- Admin frontend builds successfully.
- Client display frontend builds successfully.
- Existing snapshot reports without narrative still render.
- Reviewed narrative can be included in snapshot payload.
- Public payload contains only final reviewed narrative.
- Customer report renders narrative in the agreed location.
- Real TradingAgents smoke test has succeeded or degraded acceptably for `600519.SH -> 600519.SS`, saved as a normal smoke/test narrative run.
- Documentation explains setup, operation, disabled state, smoke test, and limitations.

