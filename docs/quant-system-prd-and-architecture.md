# Personal Quant System PRD and Architecture

Date: 2026-06-01
Status: Approved design direction

## 1. Product Goal

Build a personal quantitative strategy system for fixed stock portfolios and single-stock rule-based strategies. The system has two separate web frontends:

- Admin frontend: the primary working system where most real features live.
- Client display frontend: a read-only strategy report page used to show customers strategy performance with rich, credible visuals.

The first version does not support real-money trading. It focuses on data, strategy configuration, backtesting, paper simulation, publishing reviewed snapshots, and customer-facing presentation.

## 2. First-Version Decisions

| Topic | Decision |
|---|---|
| Primary user | Internal operator/admin |
| Client access | Read-only display through share link plus token/password |
| Trading scope | No live trading in V1 |
| Strategy scope | Fixed portfolio/single stock, rule-based strategies |
| Built-in strategy | Rolling T/grid strategy with moving-average filter |
| Strategy extensibility | Metadata-driven strategy templates generate admin forms automatically |
| Data source | Public data source auto-fetch plus CSV import fallback |
| Data frequency | Common minute bars and daily bars; default 5-minute bars |
| Historical range | Prefer recent 1-3 years for minute bars |
| Client display data | Reviewed and published static backtest snapshots |
| Admin auth | Admin login plus operation logs |
| Scheduler | Built-in backend scheduler with manual and periodic tasks |
| Deployment | Server deployment; client display accessible externally; admin restricted |
| Tech stack | Python FastAPI + React/Vite + ECharts/Lightweight Charts |
| vn.py role | Bottom-layer capability/reference architecture; new Web system is independent |

## 3. Non-Goals for V1

The first version must not include:

- Automatic live trading.
- Customer-side strategy parameter editing.
- Complete customer account system.
- Multi-role permission model.
- Tick-level data.
- Machine learning, AI prediction, or complex multi-factor stock selection.
- Real-time customer-facing strategy signal stream.
- In-place mutation of published snapshots.
- Full RPC service split around vn.py.

## 4. Recommended Architecture

```text
Admin Frontend
  -> stock/portfolio management
  -> data management
  -> strategy templates
  -> backtest tasks
  -> paper simulation
  -> snapshot publishing
  -> share links
  -> logs

Client Display Frontend
  -> one public report page per published snapshot
  -> token/password protected
  -> read-only charts and metrics

FastAPI Backend
  -> auth and permissions
  -> strategy registry
  -> data APIs
  -> backtest orchestration
  -> paper simulation scheduler
  -> snapshot publishing/versioning
  -> operation logs

Quant Layer
  -> strategy runtime
  -> rolling T/grid strategy
  -> moving-average filter
  -> metrics calculation
  -> vn.py capability reuse/reference

Database
  -> portfolios
  -> instruments
  -> bars
  -> strategy templates
  -> backtest runs
  -> paper simulation records
  -> published snapshots
  -> share tokens
  -> operation logs
```

The core boundary is: frontends never own trading or strategy logic. They call backend APIs. The backend owns workflow, persistence, permissions, publishing, and task scheduling. The quant layer owns strategy execution and metrics.

## 5. Major Modules

### 5.1 Admin Frontend

The admin frontend is the operational center. It should contain eight first-version modules:

1. Stock/portfolio management
2. Market data management
3. Strategy template management
4. Backtest task management
5. Paper simulation management
6. Strategy snapshot publishing
7. Client/share link management
8. System and operation logs

Admin UX should be utilitarian, dense, and predictable. It is a workbench, not a marketing page.

### 5.2 Client Display Frontend

The display frontend is a single strategy report page. One share link maps to one published snapshot.

The report must include:

1. Strategy name, stock/portfolio, backtest range, generation time
2. Key metrics: cumulative return, annualized return, max drawdown, win rate, trade count, profit/loss ratio
3. Strategy equity curve vs benchmark curve
4. Drawdown curve
5. Candlestick chart with buy/sell markers
6. Position curve
7. Trade detail table
8. Strategy description and risk disclosure

The visual style should be professional, credible, and chart-rich. Motion and visual polish are allowed only when they improve understanding or trust.

### 5.3 Backend API

The backend exposes APIs for both frontends and owns the main business workflow:

- Admin login/session management.
- Strategy template discovery from metadata.
- Data fetch/import task creation.
- Backtest task creation and result storage.
- Paper simulation task control.
- Snapshot review, publish, revoke, and versioning.
- Share link and token validation.
- Operation log persistence.

### 5.4 Strategy Registry

Strategies should be metadata-driven. A strategy module declares:

- Strategy id
- Display name
- Description
- Supported instrument scope
- Supported bar frequencies
- Parameter schema
- Default parameter values
- Validation rules
- Output metrics and chart data contracts

The admin frontend reads this metadata through the backend and automatically renders the configuration form. Adding a new strategy should not require changing frontend form code.

Strategy parameter sets are saved backend objects. The admin frontend may render and submit forms from strategy metadata, but it must not own strategy defaults or validation logic. When a parameter set is saved:

- The backend validates the requested `strategy_id` against the registry.
- Missing parameter values are filled from registry defaults.
- Numeric bounds, integer values, booleans, and select options are validated by the backend.
- The persisted parameter object is the fully normalized parameter set used later by backtests and paper simulations.
- Save actions are recorded in operation logs.

### 5.5 Quant and Backtest Layer

V1 includes a rolling T/grid strategy with optional moving-average filter.

Expected behavior:

- Works on a single stock or fixed portfolio.
- Uses 5-minute bars by default.
- Generates buy/sell signals from configured grid/threshold rules.
- Applies moving-average filter if enabled.
- Records trades, positions, equity, drawdown, and metrics.
- Outputs a reproducible result object for publishing.

The first executable backtest slice is intentionally narrow: single instrument, stored bars, saved strategy parameter set, deterministic result generation. It stores `BacktestRun.metrics` and `BacktestRun.result_payload` with the same major groups expected by the future client snapshot: metrics, equity curve, benchmark curve, drawdown curve, candles, trade markers, position curve, trade table, and risk disclosure. Portfolio weighting, richer fill simulation, fee/slippage, and benchmark selection can be layered onto this contract.

### 5.6 Paper Simulation

Paper simulation is quasi-real-time, not real exchange-grade order matching.

It should:

- Run manually or periodically.
- Read latest available bars.
- Generate signals.
- Simulate fills using deterministic rules.
- Record simulated trades, positions, and equity.
- Fail clearly when required data is missing.

It should not:

- Handle live broker order states.
- Support real order cancellation/replacement complexity.
- Pretend to be live trading.

## 6. Snapshot Publishing Rules

Published snapshots are immutable.

Allowed actions:

- Publish a reviewed backtest result as a new snapshot.
- Revoke an existing snapshot.
- Create a new version from a previous snapshot.

Disallowed action:

- Modify published data, metrics, or chart results in place.

Each published snapshot must save enough metadata to reproduce or audit the result:

- Strategy id and strategy version
- Strategy parameter values
- Stock/portfolio definition
- Bar frequency
- Backtest start and end time
- Data source and data version/fetch timestamp
- Fee and slippage settings
- Benchmark configuration
- Generated metrics
- Chart series
- Trade records
- Generation time
- Publisher/admin user

The first share-link implementation uses an opaque token generated at publish time. The token is stored only as a hash in the database. Public clients can read a published snapshot through the token endpoint, but revoked snapshots and inactive share links must return not found. Admins can list share links, revoke an individual link, and create a new link for a published snapshot; the clear-text token is returned only when the link is created. Revoking a snapshot disables all associated share links without mutating the snapshot payload.

## 7. Data Flow

### 7.1 Backtest to Published Report

```text
Admin creates backtest task
  -> backend validates strategy parameters
  -> backend loads historical bars
  -> quant layer runs strategy
  -> backend stores backtest result
  -> admin reviews result
  -> admin publishes snapshot
  -> backend creates share token
  -> client opens report link
  -> display frontend loads immutable snapshot
```

### 7.2 Data Fetch Failure

```text
Data task starts
  -> public data source fails or data missing
  -> backend records failure reason
  -> admin sees task failure
  -> backtest/paper task fails clearly
  -> already-published client snapshots remain available
```

The system must not silently continue with incomplete data when running backtests or paper simulations.

### 7.3 V1 CSV Market Data Import

Before public data auto-fetch is complete, the V1 admin workbench supports CSV text import as the deterministic fallback path.

Required CSV columns:

```text
timestamp,open,high,low,close,volume
```

Import rules:

- The admin selects one instrument and one bar frequency before importing.
- `timestamp` is parsed as ISO-like local datetime text, for example `2026-01-02 09:35:00`.
- `open`, `high`, `low`, `close`, and `volume` must be numeric.
- Re-importing the same instrument, frequency, and timestamp updates the existing bar instead of creating duplicate bars.
- Each import creates a `DataImportTask` row with status, row count, and failure message.
- Failed imports must not partially persist bars.
- Import actions and failures are recorded in operation logs.

The first admin UI includes a textarea-based CSV importer plus a manual public-data fetch task. Public fetch uses akshare when it is installed and records a failed task with a clear message when the provider is unavailable or returns no data. File upload and scheduled akshare fetch can be layered on top of the same backend service later.

## 8. Suggested Data Objects

| Object | Purpose |
|---|---|
| User | Admin account |
| Instrument | Stock/security metadata |
| Portfolio | Fixed list of instruments and weights |
| Bar | OHLCV market data |
| DataImportTask | Public fetch or CSV import task |
| StrategyTemplate | Metadata-declared strategy definition |
| StrategyParameterSet | Saved parameter values |
| BacktestRun | One backtest execution |
| BacktestResult | Metrics, chart series, and trades |
| PaperRun | Paper simulation configuration |
| PaperSignal | Generated simulated signal |
| PaperTrade | Simulated fill |
| PublishedSnapshot | Immutable client-facing report data |
| ShareLink | Token/password access record |
| OperationLog | Admin audit log |

## 9. Technology Choices

### Backend

- Python
- FastAPI
- SQLAlchemy or SQLModel
- APScheduler for V1 background scheduling
- SQLite for local development
- PostgreSQL for server deployment

### Frontends

- React
- Vite
- TypeScript
- ECharts for report metrics and curves
- Lightweight Charts for candlestick chart with buy/sell markers

### Quant Layer

- Python strategy modules
- vn.py used as capability reference and optional lower-level library
- Clear adapter layer between backend business objects and strategy runtime

## 10. Development Milestones

### Milestone 1: Skeleton and Data Model

- Create backend project structure.
- Add database models.
- Add admin login.
- Add operation logging base.
- Add two frontend apps.

### Milestone 2: Market Data

- Add instrument/portfolio management.
- Add public data fetch task.
- Add CSV import.
- Store bars.
- Add data completeness checks.

### Milestone 3: Strategy Registry

- Add metadata-driven strategy template registry.
- Add rolling T/grid strategy template.
- Add admin dynamic parameter form.

### Milestone 4: Backtesting

- Add backtest task creation.
- Run strategy on stored bars.
- Store metrics, trades, positions, equity, drawdown.
- Add admin result review page.

### Milestone 5: Snapshot Publishing

- Publish immutable snapshots.
- Create share links with token/password.
- Revoke snapshots.
- Preserve full reproducibility metadata.

### Milestone 6: Client Report

- Build single snapshot report page.
- Add key metrics.
- Add equity curve, benchmark curve, drawdown curve.
- Add candlestick chart with buy/sell markers.
- Add position curve and trade table.
- Add risk disclosure.

### Milestone 7: Paper Simulation

- Add quasi-real-time paper run scheduler.
- Generate simulated signals and trades.
- Store paper equity curve.
- Add admin control page.

## 11. Acceptance Criteria

V1 is acceptable when:

- Admin can log in.
- Admin can manage stocks and fixed portfolios.
- Admin can fetch/import historical data.
- Admin can configure rolling T/grid strategy through generated forms.
- Admin can run a backtest.
- Admin can review backtest metrics and charts.
- Admin can publish an immutable snapshot.
- Client can open a token-protected report link.
- Client report shows all required eight content groups.
- Published snapshots remain stable even if source data later changes.
- Data failures are visible in admin and do not corrupt reports.
- Key admin operations are recorded in operation logs.

## 12. First Places to Implement

```text
backend/
  app/
    main.py
    models/
    api/
    services/
    strategies/
    scheduler/

frontend-admin/
  src/
    pages/
    components/
    api/

frontend-display/
  src/
    pages/
    charts/
    api/
```

Keep `run_veighna.py` as a separate local VeighNa desktop entry for learning and reference. The Web system should not depend on the VeighNa desktop GUI.
