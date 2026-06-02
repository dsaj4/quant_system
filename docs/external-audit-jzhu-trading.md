# External Quant System Audit: JZhu Trading

Date: 2026-06-02
Target: `jzhu-trading/timescaledb:latest`, `jzhu-trading/all-in-one:latest`, `jzhu-trading/web-app:latest`
Observed local ports: app `8180:8180`, web `18080:80`

## 1. Confirmed Facts

- The backend image runs a Java 21 Spring Boot all-in-one service with `java -jar app.jar`.
- The web image is an Nginx-hosted React SPA. Nginx proxies `/api/` to the backend service name `app:8180`.
- The database image is a custom TimescaleDB/PostgreSQL 16 image.
- The local database container was repeatedly restarting. Logs show `initdb: error: directory "/var/lib/postgresql/data" exists but is not empty`.
- The backend logs show scheduled tasks failing because the database host `db` cannot be resolved while the DB container is unhealthy.
- The backend configuration exposes internal service domains folded into one JVM: market data, indicator, strategy, and backtest all point to `localhost:8180`.
- The backend configuration references sidecar-style public data services: `aktools` and `baostock`.
- The backend configuration enables cloud integration through `https://cloud.jzhu.net` for auth/agent workflows.
- The bundled SQL migrations create TimescaleDB hypertables for multiple K-line periods, indicator tables, strategies, backtest history, watchlist, market monitor, scan history, chart defaults, LHB data, and preset strategies.
- The web UI is a dark trading workbench with top modules for backtest analysis, strategy radar, market monitor, watchlist, strategy market, training camp, and an AI quant assistant.

## 2. Product Positioning

JZhu Trading is closer to a local quant terminal than to a client-facing reporting system. Its product surface combines:

- K-line research and backtesting.
- User-authored or AI-assisted strategies.
- Watchlists and market monitoring.
- Strategy marketplace/training guidance.
- Cloud-assisted AI and authorization.

This differs from the current project direction. Our current V1 is an internal admin system plus immutable client-facing reports. The useful lesson is not to copy its UI, but to borrow mature operational capabilities where they fit: time-series storage, data-source redundancy, indicator materialization, watchlist/monitoring, and backtest history contracts.

## 3. Architecture Observations

### Strengths

- Uses TimescaleDB hypertables for OHLCV storage, which is a stronger long-term fit than a single generic bar table once minute data volume grows.
- Separates K-line tables by period, reducing query complexity for common chart/backtest reads.
- Materializes common indicators such as MA, MACD, RSI, and BOLL.
- Keeps strategy/backtest/monitoring histories as persistent first-class concepts.
- Uses idempotent SQL migrations bundled with the backend image.
- Provides an Nginx same-origin API proxy, which makes LAN access and browser CORS simpler.
- Has a richer product loop around watchlists, scanning, signals, and AI-assisted strategy creation.

### Risks

- The all-in-one service makes local deployment simple, but it couples market data, indicator, strategy, backtest, monitor, and cloud workflows into one runtime.
- DB startup is fragile in the observed container state. The custom TimescaleDB image appears to retry initialization against a non-empty data directory.
- The app continues scheduled work while database connectivity is unavailable, creating noisy failure loops.
- Cloud integration is central to AI/auth behavior; this limits offline independence and introduces external service risk.
- The frontend exposes a broad, consumer-style tool surface. That may be attractive for self-use, but it can distract from our V1 goal of credible admin operations and client reports.
- The preset strategy migration comments imply hidden cloud-synced strategy material is used for AI recombination. This is powerful but creates auditability and explainability questions.

## 4. Comparison With Current Project

Current project strengths:

- Clear V1 boundary: no real-money trading, no customer-side parameter editing, immutable published snapshots.
- Good domain object coverage already exists: instruments, portfolios, bars, data import tasks, strategy parameter sets, backtests, paper runs, snapshots, share links, and operation logs.
- Snapshot publishing and share token behavior are more aligned with client-report trust than JZhu's terminal-style UX.
- Tests already cover market data import, data completeness, backtests, portfolio backtests, snapshot publishing, and share-link revocation.

Current project gaps exposed by the benchmark:

- Market data storage is still a single SQLite/SQLModel `Bar` table, not optimized for high-volume minute data.
- Data source coverage is narrow: akshare plus CSV fallback.
- Indicator computation and persistence are not first-class yet.
- Backtest metrics are intentionally thin and need fee, slippage, benchmark, turnover, exposure, and richer risk fields.
- There is no watchlist or monitor scan workflow yet.
- Paper simulation reuses the backtest path and does not yet record independent signal/trade lifecycle objects.
- Deployment health covers schema mismatch, but not dependency readiness, scheduler readiness, provider health, or DB connectivity degradation policies.

## 5. Modification Draft

### Phase A: Data Foundation

Keep SQLite viable for local development, but formalize a PostgreSQL/TimescaleDB deployment path.

- Add a database portability decision: SQLite for local demo, PostgreSQL/TimescaleDB for production minute data.
- Add unique constraints/indexes for `(instrument_id, frequency, timestamp)` in the current `Bar` model.
- Add explicit provider metadata fields: provider, raw symbol, exchange calendar, adjustment mode, fetch range, fetch time, provider version.
- Introduce a `DataSourceProvider` registry with `akshare`, `baostock`, and CSV as adapters behind the same contract.
- Extend health checks to report database connectivity, scheduler state, and provider availability.

### Phase B: Indicator Layer

Introduce indicator computation as a backend-owned capability, not a frontend calculation.

- Add indicator output contracts for MA, MACD, RSI, and BOLL.
- Store indicator snapshots or compute them deterministically from bars with cache metadata.
- Expose indicators through APIs used by admin review and client snapshots.
- Include indicator settings in published snapshot metadata when indicators affect strategy logic.

### Phase C: Backtest Maturity

Upgrade the backtest result contract while keeping V1 strategy scope constrained.

- Add fee, slippage, benchmark, turnover, exposure, and annualized metrics.
- Separate signal generation, simulated orders, fills, trades, positions, and equity series.
- Persist strategy version and normalized parameter set into each backtest result.
- Add sample-size and data-quality warnings directly to backtest results before publishing.
- Add regression tests for fee/slippage and benchmark behavior.

### Phase D: Monitoring And Paper Simulation

Borrow the useful part of JZhu's market monitor without becoming a broad trading terminal.

- Add admin watchlists for fixed monitoring targets.
- Add `MonitorRule` and `MonitorSignal` objects for scheduled strategy scans.
- Keep alerts internal/admin-facing in V1.
- Store paper signals and paper trades separately from backtest payload JSON.
- Add scheduler failure policies so jobs degrade cleanly when dependencies are unavailable.

### Phase E: Deployment And Operations

Strengthen reliability before adding more product surface.

- Add Docker Compose for backend, admin frontend, display frontend, and PostgreSQL/TimescaleDB.
- Add startup readiness checks before scheduler registration.
- Add non-destructive DB initialization rules and documented volume reset instructions.
- Add operation logs for scheduler runs, provider failures, monitor signals, and publish/revoke events.
- Add a production configuration checklist for CORS, auth secret, DB URL, admin exposure, and public display URL.

## 6. Formal Modification Queue

Approved-to-implement first:

1. Add model-level uniqueness/indexing for bar identity and tests for duplicate protection.
2. Add data provider registry abstraction while preserving the existing akshare and CSV behavior.
3. Extend `/api/health` with dependency readiness: database, schema, scheduler, provider registry.
4. Expand backtest result payload with fee/slippage/benchmark assumptions and richer risk metrics.
5. Create a production deployment document for PostgreSQL/TimescaleDB and scheduler readiness.

Hold for later:

- Strategy marketplace.
- Cloud AI strategy generation.
- Customer-visible live signal stream.
- Full watchlist/monitor UI.
- Hidden preset strategy libraries.
- Real broker execution.

Rejected for this project V1:

- Copying the broad terminal-style UX.
- Making AI a core dependency for backtesting or report generation.
- Letting frontend own indicator or strategy calculations.
- Publishing mutable or live-updating client reports.

## 7. Immediate Recommendation

The current project should mature from the data/backend side first. The next formal implementation should be a small, testable backend change set:

1. harden bar identity and data-source metadata,
2. introduce provider abstraction,
3. upgrade health/readiness reporting,
4. then expand backtest metrics.

This keeps the system aligned with its approved V1 goal while borrowing the best operational ideas from the external system.
