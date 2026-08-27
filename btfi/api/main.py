from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd

from btfi.strategies.registry import BUILTIN_STRATEGIES, list_strategies, get_strategy_template, make_config_from_template
from btfi.strategies.base import StrategyConfig
from btfi.strategies.formula import validate_formula
from btfi.data.cache import Cache
from btfi.data.yahoo import YahooFinanceProvider
from btfi.backtesting.engine import BacktestEngine
from btfi.analytics.metrics import period_metrics, rolling_analysis, start_date_robustness, required_periods, annual_returns
from btfi.analytics.robustness import parameter_robustness, cost_robustness
from btfi.analytics.verdict import compute_verdict
from btfi.database.store import ExperimentStore
from btfi.reports.generator import generate_markdown
from btfi.data.models import SUPPORTED_METRICS
from btfi.__version__ import __version__

app = FastAPI(title="BTFI API", version=__version__, description="Buy The Fucking Index - Strategy Backtesting Lab")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

cache = Cache()
provider = YahooFinanceProvider(cache=cache)
engine = BacktestEngine(provider)
store = ExperimentStore()

# ---------- Models ----------
class BacktestRequest(BaseModel):
    strategy_id: Optional[str] = None
    name: Optional[str] = None
    universe: str = "sp500"
    custom_tickers: Optional[List[str]] = None
    metric: str = "momentum_12m"
    formula: Optional[str] = None
    top_n: int = 20
    selection_mode: str = "top_n"
    top_pct: Optional[float] = None
    weighting: str = "equal"
    rebalance: str = "annual"
    transaction_cost_bps: float = 10
    slippage_bps: float = 5
    start_date: str = "2010-01-01"
    end_date: str = "2024-12-31"
    benchmark: str = "SPY"

class ValidateFormulaRequest(BaseModel):
    formula: str

# ---------- Routes ----------
@app.get("/")
def root():
    return {"message": "BTFI API", "version": __version__, "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}

@app.get("/strategies")
def get_strategies(category: Optional[str] = None):
    return list_strategies(category)

@app.get("/strategies/{strategy_id}")
def get_strategy(strategy_id: str):
    s = get_strategy_template(strategy_id)
    if not s:
        raise HTTPException(404, "Strategy not found")
    return s

@app.get("/metrics")
def get_supported_metrics():
    return SUPPORTED_METRICS

@app.post("/validate-formula")
def validate_formula_endpoint(req: ValidateFormulaRequest):
    ok, msg = validate_formula(req.formula, SUPPORTED_METRICS)
    return {"valid": ok, "message": msg}

@app.post("/backtests")
def run_backtest(req: BacktestRequest):
    # Build config
    if req.strategy_id:
        try:
            overrides = req.model_dump(exclude={"strategy_id"})
            # remove None strategy_id remnants
            # Filter to valid overrides
            cfg = make_config_from_template(req.strategy_id, overrides={k: v for k, v in overrides.items() if v is not None})
            # Apply explicit overrides that make_config may have missed due to custom_tickers handling
            if req.custom_tickers:
                cfg.custom_tickers = req.custom_tickers
        except Exception as e:
            raise HTTPException(400, str(e))
    else:
        cfg = StrategyConfig(
            name=req.name or "Custom Strategy",
            description="Custom",
            category="Custom",
            universe=req.universe,
            custom_tickers=req.custom_tickers,
            metric=req.metric,
            formula=req.formula,
            top_n=req.top_n,
            top_pct=req.top_pct,
            selection_mode=req.selection_mode,
            weighting=req.weighting,
            rebalance=req.rebalance,
            transaction_cost_bps=req.transaction_cost_bps,
            slippage_bps=req.slippage_bps,
            start_date=req.start_date,
            end_date=req.end_date,
            benchmark=req.benchmark,
        )
    # Validate dates
    try:
        pd.to_datetime(cfg.start_date)
        pd.to_datetime(cfg.end_date)
    except Exception:
        raise HTTPException(400, "Invalid dates")
    if cfg.start_date >= cfg.end_date:
        raise HTTPException(400, "start_date must be before end_date")

    try:
        out = engine.run(cfg)
    except Exception as e:
        raise HTTPException(500, f"Backtest failed: {e}")

    equity = out["equity"]
    bench_eq = out["benchmark_equity"]
    metrics = period_metrics(equity, bench_eq)
    rolling_1 = rolling_analysis(equity, bench_eq, 1)
    rolling_3 = rolling_analysis(equity, bench_eq, 3)
    rolling_5 = rolling_analysis(equity, bench_eq, 5)
    rolling_10 = rolling_analysis(equity, bench_eq, 10)
    periods = required_periods(equity, bench_eq)
    ann = annual_returns(equity, bench_eq)
    start_robust = start_date_robustness(equity, bench_eq, 5)
    # robustness (light to keep fast)
    try:
        param_rob = parameter_robustness(engine, cfg, "top_n", [5,10,15,20,25,30,50])
    except Exception:
        param_rob = []
    try:
        cost_rob = cost_robustness(engine, cfg)
    except Exception:
        cost_rob = []

    verdict, reason, score_components = compute_verdict(metrics, rolling_5, param_rob, cost_rob, out.get("warnings",[]))

    # Save experiment
    exp_id = store.save(
        title=cfg.name,
        config=cfg.to_dict(),
        results={
            "metrics": metrics,
            "periods": periods,
            "rolling": {"1Y": rolling_1, "3Y": rolling_3, "5Y": rolling_5, "10Y": rolling_10},
            "annual": ann.to_dict(orient="records") if not ann.empty else [],
            "start_robustness": start_robust,
            "param_robustness": param_rob,
            "cost_robustness": cost_rob,
            "equity_curve": [{"date": str(d.date()), "value": float(v)} for d, v in equity.tail(200).items()],
            "benchmark_curve": [{"date": str(d.date()), "value": float(v)} for d, v in bench_eq.tail(200).items()],
            "warnings": out.get("warnings", []),
            "reason": reason,
            "score_components": score_components,
        },
        verdict=verdict,
        btfi_score=score_components.get("btfi_score",0)
    )

    return {
        "experiment_id": f"{exp_id:03d}",
        "id": exp_id,
        "config": cfg.to_dict(),
        "metrics": metrics,
        "periods": periods,
        "rolling": {"1Y": rolling_1, "3Y": rolling_3, "5Y": rolling_5, "10Y": rolling_10},
        "annual_returns": ann.to_dict(orient="records") if not ann.empty else [],
        "start_robustness": start_robust,
        "param_robustness": param_rob,
        "cost_robustness": cost_rob,
        "verdict": verdict,
        "verdict_reason": reason,
        "btfi_score": score_components,
        "warnings": out.get("warnings", []),
        "equity_curve": [{"date": str(d.date()), "value": float(v)} for d, v in equity.tail(500).items()],
        "benchmark_curve": [{"date": str(d.date()), "value": float(v)} for d, v in bench_eq.tail(500).items()],
    }

@app.get("/experiments")
def list_experiments(limit: int = Query(50, ge=1, le=200)):
    return store.list(limit)

@app.get("/experiments/{eid}")
def get_experiment(eid: int):
    exp = store.get(eid)
    if not exp:
        raise HTTPException(404, "Experiment not found")
    return exp

@app.delete("/experiments/{eid}")
def delete_experiment(eid: int):
    exp = store.get(eid)
    if not exp:
        raise HTTPException(404, "Not found")
    store.delete(eid)
    return {"deleted": eid}

@app.get("/experiments/{eid}/markdown")
def export_markdown(eid: int):
    exp = store.get(eid)
    if not exp:
        raise HTTPException(404, "Not found")
    cfg = exp["config"]
    res = exp["results"]
    # reconstruct annual df
    ann_list = res.get("annual", [])
    ann_df = pd.DataFrame(ann_list)
    rolling5 = res.get("rolling", {}).get("5Y", {}) if isinstance(res.get("rolling"), dict) else {}
    md = generate_markdown(
        experiment_id=exp["id"],
        title=exp["title"],
        config=cfg,
        metrics=res.get("metrics", {}),
        annual_df=ann_df,
        verdict=exp.get("verdict",""),
        verdict_reason=res.get("reason",""),
        warnings=res.get("warnings",[]),
        rolling=rolling5,
        btfi_score_components=res.get("score_components", {}),
    )
    return PlainTextResponse(md, media_type="text/markdown")

@app.get("/data-quality")
def data_quality():
    meta = cache.metadata()
    size = cache.cache_size_mb()
    # count files
    return {
        "cache_size_mb": size,
        "datasets": meta.to_dict(orient="records") if not meta.empty else [],
        "warnings": [
            "⚠ Historical constituent data unavailable. Survivorship bias may materially affect results.",
            "⚠ Potential look-ahead bias: historical publication dates are unavailable for this fundamental dataset via yfinance.",
            "S&P 500 proxy: SPY used for benchmark where index data unavailable.",
        ],
        "provider": "yfinance",
        "cache_dir": str(cache.cache_dir),
    }

@app.post("/cache/clear")
def clear_cache():
    cache.clear()
    return {"cleared": True}

@app.get("/leaderboard")
def leaderboard(limit: int = 100, sort_by: str = "btfi_score"):
    exps = store.list(limit*2)
    # sort
    valid_sort = {"btfi_score","cagr","excess","sharpe"}
    # expose flattened
    rows = []
    for e in exps:
        # need metrics
        full = store.get(e["id"])
        if not full:
            continue
        metrics = full.get("results", {}).get("metrics", {})
        rows.append({
            "id": full["id"],
            "experiment": f"BTFI #{full['id']:03d}",
            "strategy": full["title"],
            "cagr": metrics.get("cagr",0),
            "excess_cagr": metrics.get("excess_cagr",0),
            "sharpe": metrics.get("sharpe",0),
            "max_drawdown": metrics.get("max_drawdown",0),
            "verdict": full.get("verdict",""),
            "btfi_score": full.get("btfi_score",0),
            "win_rate_5y": full.get("results",{}).get("rolling",{}).get("5Y",{}).get("beat_pct",0) if isinstance(full.get("results",{}).get("rolling"),dict) else 0,
            "created_at": full.get("created_at",""),
        })
    # sort
    key_map = {"btfi_score": lambda x: x["btfi_score"], "cagr": lambda x: x["cagr"], "excess": lambda x: x["excess_cagr"], "sharpe": lambda x: x["sharpe"]}
    rows = sorted(rows, key=key_map.get(sort_by, key_map["btfi_score"]), reverse=True)
    return rows[:limit]

@app.get("/benchmarks")
def benchmarks():
    return [{"id": "SPY", "name": "S&P 500 proxy: SPY", "description": "SPDR S&P 500 ETF"}]
