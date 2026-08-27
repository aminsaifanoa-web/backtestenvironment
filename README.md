# BTFI — Buy The Fucking Index

**A professional quantitative research platform disguised as a ridiculously simple experiment machine.**

Test whether your investment idea actually beats the S&P 500 — rigorously, transparently, reproducibly.

## Quick Start

```bash
pip install -r requirements.txt
# Backend
uvicorn btfi.api.main:app --reload --port 8000
# Frontend (separate terminal)
cd frontend && npm install && npm run dev
# Or Docker
docker-compose up --build
```

Open http://localhost:5173 — click **RUN YOUR FIRST EXPERIMENT**.

## CLI

```bash
btfi run --strategy low_pe --stocks 20 --rebalance annual
btfi compare 001 002 003
btfi export 001 --format markdown
btfi list-strategies
```

## API

```
POST /backtests
GET  /backtests/{id}
GET  /strategies
GET  /experiments
GET  /benchmarks
GET  /leaderboard
GET  /data-quality
```

## Philosophy

> The burden of proof is on the strategy, not the index.

Default hypothesis: *Buy the S&P 500 and do nothing.* A strategy must show meaningful outperformance, reasonable risk, persistence, robustness, and survival after realistic costs.

## Data

- **ONLY** external source: Yahoo Finance via `yfinance` (no API key).
- Local cache: Parquet + DuckDB (`data/cache/btfi.duckdb`).
- Workflow: request → check cache → download → validate → cache → use.

### Limitations (never hidden)

- ⚠ Historical constituent data unavailable → survivorship bias warning on every S&P 500 backtest.
- ⚠ Point-in-time fundamental publication dates unavailable via yfinance → look-ahead bias warning.
- S&P 500 measured as **SPY proxy**, clearly labeled.

## Architecture

```
btfi/data/        Provider abstraction + YahooFinanceProvider + cache
btfi/strategies/  Modular Strategy classes + formula parser (safe, no exec)
btfi/backtesting/ Event/time-series engine with t+1 execution
btfi/portfolio/   Holdings, cash, costs, dividends/splits
btfi/analytics/   CAGR, Sharpe, Sortino, drawdown, alpha/beta, rolling, robustness
btfi/reports/     Markdown publication generator
btfi/api/         FastAPI
btfi/database/    Experiment store (DuckDB + JSON fallback)
```

## Demo Mode

Works immediately without downloads: synthetic price paths seeded deterministically, labeled `DEMO DATA — NOT REAL INVESTMENT RESULTS`.

## Reproducibility

Every experiment saves immutable config + data timestamp + cache version + app version. Identical config + identical cached dataset → identical results.

## Testing

```bash
pytest -q
```

Covers: financial math, portfolio accounting, look-ahead prevention, parameter isolation, formula parser safety.
