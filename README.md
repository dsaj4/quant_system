# Quant System

Personal quantitative strategy system workspace.

Current status:

- VeighNa/vn.py desktop entry is available through `run_veighna.py`.
- Product requirements and architecture are documented in `docs/quant-system-prd-and-architecture.md`.
- The planned Web system uses a FastAPI backend plus two React/Vite frontends: one admin frontend and one client display frontend.

## Local Setup

Use Python 3.13 on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Start VeighNa Desktop

```powershell
.\.venv\Scripts\python.exe run_veighna.py
```

## Start Web Development Skeleton

Backend API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Admin frontend:

```powershell
cd frontend-admin
npm.cmd install
npm.cmd run dev
```

Client display frontend:

```powershell
cd frontend-display
npm.cmd install
npm.cmd run dev
```

Default local URLs:

- Backend health check: `http://127.0.0.1:8000/api/health`
- Strategy metadata API: `http://127.0.0.1:8000/api/strategies`
- Admin frontend: `http://127.0.0.1:5183`
- Client display frontend: `http://127.0.0.1:5184`

## Current Web Skeleton Features

- Admin login with the local seed account `admin / admin`.
- Instrument and fixed-portfolio management.
- Metadata-driven strategy registry endpoint.
- CSV market data import through the admin frontend.
- Manual public market data fetch task through akshare when available.
- Recent bar query and data import task list.
- Saved strategy parameter sets generated from backend strategy metadata.
- Single-instrument rolling T/grid backtests using stored bars.
- Admin backtest review panel for metrics, curves, positions, and trade details before publishing.
- Manual paper simulation runs using the same backend strategy path.
- Immutable snapshot publishing with revocation and tokenized client report links.
- Client display report page that loads published snapshots by token and renders ECharts/Lightweight Charts reports.
- Operation logs for login, instrument, portfolio, market data, strategy, backtest, paper run, and snapshot actions.

CSV market data import currently expects:

```csv
timestamp,open,high,low,close,volume
2026-01-02 09:35:00,10,10.5,9.8,10.2,1000
2026-01-02 09:40:00,10.2,10.8,10.1,10.7,1200
```

## Documents

- `docs/quant-system-prd-and-architecture.md`: approved V1 PRD and architecture direction.
