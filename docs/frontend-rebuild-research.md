# Frontend Rebuild Research And Design Draft

Date: 2026-06-02
Status: implemented and verified for the agreed admin P0 / display P1 frontend rebuild scope

## 1. Scope

This round is a frontend-only rebuild for:

- `frontend-admin/`: P0. Turn the current single-page module stack into a professional quant research workspace.
- `frontend-display/`: P1. Keep the existing report capability and make only restrained reliability/style refinements.

No backend API, database schema, payload field, trading rule, provider semantics, or migration change is included in this draft.

## 2. Research Notes

### Quant Research Workspace

References:

- SteadyTape: recent runs and full-screen study reports are visible from top navigation.
- Forven: strategy ideas move through visible stages before any live-capital promotion.
- Traseq: explicitly positions itself as a research workspace, not an execution platform.

Borrow:

- Make recent runs, reports, and workflow stage visible before deep tables.
- Separate research, verification, publication, and paper monitoring language.
- Keep a strong boundary between simulated research and live trading.

Do not borrow:

- Live-trading affordances, exchange connection language, or promotion-to-live controls.
- Marketing-style hero pages inside the admin product.

Landing in this project:

- Use a left navigation grouped by demo workflow: Overview, Data, Strategy, Backtest, Publish, Paper, Audit.
- Put the demo route as a horizontal command rail: select/create instrument -> fetch data -> check quality -> choose parameters -> run backtest -> publish snapshot -> open/copy report -> inspect paper run.
- Keep paper run copy as simulated monitoring.

### Data Pipeline And Task Tables

References:

- SaaS data pipeline admin patterns: status-first tables, compact filters, error messages near failed jobs.
- Ant Design admin patterns already used by the project: dense tables, inline forms, tags, alerts, and expandable rows.

Borrow:

- Status columns should be visually scannable.
- Failed tasks need a reason column that is not hidden in secondary detail.
- Long operational tables need fixed scroll or pagination.

Do not borrow:

- Overly decorative cards or nested card dashboards.
- Generic monitoring noise that hides the next demo action.

Landing in this project:

- Data module gets a two-column workbench: command form on the left, task/quality evidence on the right.
- Provider status is explicit: Tushare primary, AkShare fallback, JQData/BaoStock reserved or disabled.
- Import tasks and schedules remain existing API-backed tables, but are arranged as evidence beneath the active task.

### Backtest And Report Review

References:

- Portfolio analytics dashboards: returns, drawdown, Sharpe/win rate, trade count, and risk language are grouped by decision value.
- Risk report tools: drawdown and data-quality warnings are surfaced with the main result, not buried at the bottom.

Borrow:

- Treat cumulative return and drawdown as a paired reading, including negative-result explanation.
- Show result review before publication action.
- Put report publication status next to share-link action.

Do not borrow:

- Crowded trading terminal layouts.
- Visual language that implies execution or order management.

Landing in this project:

- Backtest module becomes a split review page: run form + backtest list on one side, selected run review and publish preparation on the other.
- Snapshot and share-link tables are grouped under "Publication" rather than separate top-level fragments.
- Latest share token is shown only as a temporary success message from the API response; no token is written to docs.

## 3. Visual Direction

Direction: restrained research operations.

Principles:

- Quiet light workspace, high density, no large gradients, no card nesting.
- Borders and typographic hierarchy do most of the work.
- Use warm warning and red risk states sparingly, with blue/teal only as action or data accents.
- Keep Ant Design components, `@ant-design/icons`, `echarts`, and `lightweight-charts`.

Admin tone:

- Internal cockpit, not landing page.
- Compact, precise, demo-operator friendly.

Display tone:

- Mature investment research report.
- First screen should answer: what strategy, what target, what period, what result, what risk, what data basis.

## 4. Decisions Aligned With User

- Primary focus: `frontend-admin` is the main battlefield; `frontend-display` gets only restrained refinements.
- Navigation: left sidebar module navigation plus a top demo command rail.
- Overview: demo command center first, system operations second.
- Instruments and portfolios: no separate top-level module; place them in the Data workspace.
- Data workflow: public market-data fetch is primary; CSV is an offline fallback in the same workspace.
- Backtest workflow: recent run list plus single selected run review; no multi-run comparison this round.
- Publication workflow: merge snapshot publishing and share-link management into one customer-report pipeline.
- Paper workflow: audit-record feel first, light monitoring feel second; avoid live-trading terminal language.
- Audit workflow: use existing operation logs and provider/system boundary notes; do not add health/schema API calls this round.
- Visual tone: precise, quiet research workspace; not pure white minimalism and not a dark trading terminal.
- Admin structure: split `frontend-admin/src/App.tsx` into section-level files and a few shared components.
- Display structure: do not split `frontend-display` into new component files this round.
- Routing: do not add React Router or hash routing; section switching stays in React state.
- New files: allowed under `frontend-admin/src/components/`, `frontend-admin/src/sections/`, and `frontend-admin/src/utils/`.
- Layout primitives: keep Ant Design forms, tables, buttons, tags, and alerts; reduce `Card` as the page structure driver.
- Share links: add a copy/open action only for the latest token returned after publish/create; do not persist or reconstruct historical tokens.
- Demo command rail: each step is clickable and jumps to the corresponding section, but does not enforce a locked wizard.
- Mobile scope: desktop/projection first; mobile must not overlap or break, but does not need a dedicated high-efficiency workflow.
- Display K-line panel: moderately reduce the dark trading-terminal feel.
- Negative performance explanation: do not add special "negative return is not a demo failure" emphasis; keep existing professional risk disclosure.

## 5. Admin Information Architecture

### Proposed Navigation

- Overview: system health snapshot, demo command rail, latest backtest/report/paper run.
- Data: instruments, portfolios, public fetch, CSV fallback, data quality, import tasks, schedules.
- Strategy: strategy template, parameter-set editor, saved parameter sets.
- Backtest: run backtest, compare recent runs, inspect selected run curves/trades/signals.
- Publication: publish snapshot, create/revoke share link, open client report.
- Paper: create paper run, status timeline, simulated signal/trade detail, failure reason.
- Audit: operation logs, provider notes, system boundaries.

### Demo Path

The admin page should visually support this route:

```text
Instrument
  -> Market Data
  -> Data Quality
  -> Parameters
  -> Backtest
  -> Review
  -> Snapshot
  -> Share Link
  -> Paper Run
```

## 6. File-Level Change Draft

### `frontend-admin/src/App.tsx`

Planned changes:

- Keep existing API client and handlers.
- Add front-end-only state for selected workspace section.
- Replace the single long `workspace` stack with section-level components.
- Keep high-level data loading, forms, and handler ownership in `App.tsx` unless a clean extraction is obvious.
- Pass only the necessary state and handlers into each section.
- Avoid introducing a new routing dependency or a new app-wide state library.

### `frontend-admin/src/sections/*`

Planned new files:

- `OverviewSection.tsx`
- `DataSection.tsx`
- `StrategySection.tsx`
- `BacktestSection.tsx`
- `PublicationSection.tsx`
- `PaperSection.tsx`
- `AuditSection.tsx`

Each section owns its view structure only. It should not define API calls or change request payloads.

### `frontend-admin/src/components/*`

Planned new files as needed:

- `MetricTile.tsx`
- `StatusTag.tsx`
- `CommandRail.tsx`
- `SectionShell.tsx`
- `CopyLinkButton.tsx`

These should stay small and presentational.

### `frontend-admin/src/utils/*`

Planned new files as needed:

- `format.ts`
- `labels.ts`

Move translation/format helpers out of `App.tsx` only when it reduces duplication across sections.

Existing behavior to preserve:

- Reuse existing forms and tables, but reorganize them into split work surfaces.
- Add compact summary strips for latest data task, latest selected backtest, latest snapshot, latest paper run.
- Add clear copy around providers: Tushare primary, AkShare fallback, JQData/BaoStock reserved.
- Do not alter API request payloads or response types.

### `frontend-admin/src/App.css`

Planned changes:

- Replace card-stack layout with:
  - fixed sidebar
  - compact top bar
  - command rail
  - two-column work surfaces
  - scroll-safe table areas
- Add responsive rules for projection width, tablet, and mobile.
- Keep radius at 6-8px and avoid nested card styling.

### `frontend-display/src/App.tsx`

Planned changes:

- Keep payload normalization and existing chart logic.
- Optionally tighten hero text and risk interpretation labels.
- Keep old snapshot fallbacks for missing fields.
- Do not add special explanatory emphasis for negative returns beyond the current professional risk-disclosure pattern.
- No public API changes.

### `frontend-display/src/App.css`

Planned changes:

- Refine hero density and mobile chart/table behavior.
- Reduce one-note dark emphasis in the K-line section if it visually overpowers the report.
- Ensure long words and table text wrap safely on narrow screens.

## 7. Compatibility And Stop Conditions

Compatible:

- Existing share tokens and old snapshots should continue to open.
- Missing report fields remain handled by current fallbacks.
- API failures still show visible errors.
- Disabled providers stay disabled.

Stop and ask before changing:

- Any backend endpoint shape.
- Any payload field name.
- Any database model or migration.
- Any wording that implies live trading or automatic order execution.
- Any new paid data source invocation.

## 8. Verification Plan

Commands:

```powershell
cd frontend-admin
npm.cmd run build

cd ..\frontend-display
npm.cmd run build
```

Browser checks:

- Admin desktop: data, backtest, publication, paper, audit sections render without application console errors.
- Admin mobile/projection: no overlapping top bar, command rail, forms, or table controls.
- Display desktop: report hero, metrics, K-line evidence, trade table, assumptions, risk disclosure render.
- Display mobile: no text/table overlap; charts keep non-zero canvas dimensions.

## 9. Approval Request

First implementation pass:

1. Rebuild `frontend-admin` information architecture and layout with section-level files.
2. Build and browser-check admin.
3. Make small `frontend-display` reliability/style refinements.
4. Build and browser-check display.

Execution note:

- Completed the new admin navigation model and clickable demo command rail.
- Added shared components and connected section-level files for the active admin workspaces.
- Reorganized visible admin modules by active workspace without backend contract changes; section files now own the workspace shells while `App.tsx` keeps API handlers, form instances, and panel JSX ownership.
- Added latest share-link copy/open action for the latest token returned by publish/create.
- Removed fixed mobile min-width constraints from admin/display shells.
- Moderately reduced the client report K-line panel's dark terminal feel.
- Maintainability note: `frontend-admin/src/App.tsx` deliberately keeps form instances and API handlers at the top level. The connected section files own workspace grouping; a future cleanup can split individual panels further if the team later wants finer ownership boundaries.
