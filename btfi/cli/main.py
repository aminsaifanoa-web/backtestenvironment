from __future__ import annotations
import json
import typer
from pathlib import Path
import pandas as pd

from btfi.strategies.registry import make_config_from_template, get_strategy_template, BUILTIN_STRATEGIES
from btfi.data.cache import Cache
from btfi.data.yahoo import YahooFinanceProvider
from btfi.backtesting.engine import BacktestEngine
from btfi.analytics.metrics import period_metrics, rolling_analysis, annual_returns
from btfi.analytics.verdict import compute_verdict
from btfi.analytics.robustness import parameter_robustness, cost_robustness
from btfi.reports.generator import generate_markdown
from btfi.database.store import ExperimentStore

app = typer.Typer(help="BTFI - Buy The Fucking Index CLI")

@app.command()
def run(
    strategy: str = typer.Option("low_pe", help="Strategy template ID"),
    stocks: int = typer.Option(20, help="Top N"),
    rebalance: str = typer.Option("annual", help="Rebalance frequency"),
    start: str = typer.Option("2010-01-01", help="Start date"),
    end: str = typer.Option("2024-12-31", help="End date"),
    benchmark: str = typer.Option("SPY", help="Benchmark ticker"),
    cost: float = typer.Option(10, help="Transaction cost bps"),
    weighting: str = typer.Option("equal", help="Weighting scheme"),
    universe: str = typer.Option("sp500", help="Universe"),
):
    """Run a backtest. Example: btfi run --strategy low-pe --stocks 20 --rebalance annual"""
    # normalize strategy id
    sid = strategy.replace("-", "_")
    cache = Cache()
    provider = YahooFinanceProvider(cache=cache)
    engine = BacktestEngine(provider)
    try:
        cfg = make_config_from_template(sid, overrides={
            "top_n": stocks, "rebalance": rebalance, "start_date": start, "end_date": end,
            "benchmark": benchmark, "transaction_cost_bps": cost, "weighting": weighting, "universe": universe
        })
    except Exception:
        # custom strategy
        from btfi.strategies.base import StrategyConfig
        cfg = StrategyConfig(name=strategy, universe=universe, metric=strategy, top_n=stocks, rebalance=rebalance, start_date=start, end_date=end, benchmark=benchmark, transaction_cost_bps=cost, weighting=weighting)
    typer.echo(f"Running {cfg.name} ({cfg.metric}) {cfg.top_n} stocks, rebalance {cfg.rebalance} ...")
    out = engine.run(cfg)
    equity = out["equity"]
    bench = out["benchmark_equity"]
    metrics = period_metrics(equity, bench)
    rolling5 = rolling_analysis(equity, bench, 5)
    typer.echo(f"CAGR: {metrics['cagr']*100:.2f}% vs S&P {metrics['benchmark_cagr']*100:.2f}% (Excess {metrics['excess_cagr']*100:.2f}%)")
    typer.echo(f"Sharpe {metrics['sharpe']:.2f} | MaxDD {metrics['max_drawdown']*100:.1f}%")
    if rolling5.get("win_rate") is not None:
        typer.echo(f"5Y win rate: {rolling5['beat_pct']}%")
    for w in out.get("warnings",[]):
        typer.echo(f"WARN: {w}")
    # verdict
    param_r = parameter_robustness(engine, cfg)
    cost_r = cost_robustness(engine, cfg)
    verdict, reason, score = compute_verdict(metrics, rolling5, param_r, cost_r, out.get("warnings",[]))
    typer.echo(f"Verdict: {verdict} — {reason}")
    typer.echo(f"BTFI Score: {score['btfi_score']}")

@app.command()
def compare(ids: str = typer.Argument(..., help="Space or comma separated experiment IDs")):
    """Compare experiments. Example: btfi compare 001 002 003"""
    store = ExperimentStore()
    parts = [p.strip().zfill(3) for p in ids.replace(",", " ").split() if p.strip()]
    for pid in parts:
        eid = int(pid)
        exp = store.get(eid)
        if not exp:
            typer.echo(f"#{pid} not found")
            continue
        metrics = exp.get("results",{}).get("metrics",{})
        typer.echo(f"BTFI #{eid:03d} {exp['title']:40} CAGR {metrics.get('cagr',0)*100:6.2f}% Excess {metrics.get('excess_cagr',0)*100:6.2f}% Sharpe {metrics.get('sharpe',0):4.2f} Verdict {exp.get('verdict','')}")

@app.command()
def export(
    experiment_id: str = typer.Argument(..., help="Experiment ID e.g. 001"),
    format: str = typer.Option("markdown", help="markdown, json, csv"),
    output: str = typer.Option(None, help="Output file path"),
):
    """Export experiment. Example: btfi export 001 --format markdown"""
    eid = int(experiment_id)
    store = ExperimentStore()
    exp = store.get(eid)
    if not exp:
        typer.echo(f"Experiment {experiment_id} not found")
        raise typer.Exit(1)
    cfg = exp["config"]
    res = exp["results"]
    if format == "markdown":
        ann = pd.DataFrame(res.get("annual",[]))
        md = generate_markdown(eid, exp["title"], cfg, res.get("metrics",{}), ann, exp.get("verdict",""), res.get("reason",""), res.get("warnings",[]), res.get("rolling",{}).get("5Y",{}), res.get("score_components",{}))
        out_path = Path(output) if output else Path(f"btfi-{eid:03d}.md")
        out_path.write_text(md)
        typer.echo(f"Exported to {out_path}")
    elif format == "json":
        out_path = Path(output) if output else Path(f"btfi-{eid:03d}.json")
        out_path.write_text(json.dumps(exp, indent=2, default=str))
        typer.echo(f"Exported to {out_path}")
    elif format == "csv":
        eq = res.get("equity_curve",[])
        df = pd.DataFrame(eq)
        out_path = Path(output) if output else Path(f"btfi-{eid:03d}.csv")
        df.to_csv(out_path, index=False)
        typer.echo(f"Exported to {out_path}")
    else:
        typer.echo(f"Unknown format {format}")

@app.command()
def list_strategies():
    """List available strategies"""
    for s in BUILTIN_STRATEGIES:
        typer.echo(f"{s['id']:25} {s['category']:12} {s['name']}")

if __name__ == "__main__":
    app()
