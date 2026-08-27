from __future__ import annotations
import pandas as pd
import numpy as np
from btfi.strategies.base import StrategyConfig
from btfi.analytics.metrics import cagr

def parameter_robustness(engine, base_config: StrategyConfig, param: str = "top_n", values: list | None = None) -> list[dict]:
    if values is None:
        if param == "top_n":
            values = [5,10,15,20,25,30,50]
        elif param == "rebalance":
            values = ["monthly","quarterly","semiannual","annual"]
        else:
            values = [5,10,20]
    results = []
    for v in values:
        cfg = StrategyConfig(**{**base_config.__dict__, param: v})
        # ensure extra_params copied
        cfg.extra_params = base_config.extra_params.copy()
        if param in cfg.extra_params:
            cfg.extra_params[param] = v
            # also set attribute if needed
            try:
                setattr(cfg, param, v)
            except Exception:
                pass
        try:
            out = engine.run(cfg)
            eq = out["equity"]
            be = out["benchmark_equity"]
            s_cagr = cagr(eq)
            b_cagr = cagr(be)
            results.append({"param": param, "value": v, "strategy_cagr": s_cagr, "benchmark_cagr": b_cagr, "excess": s_cagr - b_cagr, "error": None})
        except Exception as e:
            results.append({"param": param, "value": v, "error": str(e)})
    return results

def cost_robustness(engine, base_config: StrategyConfig) -> list[dict]:
    bps_values = [0,10,25,50,100]
    results = []
    for bps in bps_values:
        cfg = StrategyConfig(**{**base_config.__dict__, "transaction_cost_bps": float(bps)})
        cfg.extra_params = base_config.extra_params.copy()
        try:
            out = engine.run(cfg)
            eq = out["equity"]
            be = out["benchmark_equity"]
            s_cagr = cagr(eq)
            b_cagr = cagr(be)
            results.append({"cost_bps": bps, "strategy_cagr": s_cagr, "benchmark_cagr": b_cagr, "excess": s_cagr - b_cagr})
        except Exception as e:
            results.append({"cost_bps": bps, "error": str(e)})
    return results

def walk_forward(engine, base_config: StrategyConfig, train_years: int = 5, test_years: int = 1) -> dict:
    # Simplified walk-forward: rolling windows, no param optimization (just report test CAGR)
    from btfi.analytics.metrics import cagr
    try:
        out = engine.run(base_config)
        eq = out["equity"]
        be = out["benchmark_equity"]
        # create walk windows across full history
        train_days = train_years*252
        test_days = test_years*252
        step = test_days
        windows = []
        for start_idx in range(0, len(eq)-train_days-test_days, step):
            train_end = start_idx + train_days
            test_start = train_end
            test_end = test_start + test_days
            test_eq = eq.iloc[test_start:test_end+1]
            test_be = be.iloc[test_start:test_end+1]
            if len(test_eq) < test_days*0.8:
                continue
            windows.append({
                "train_start": str(eq.index[start_idx].date()),
                "train_end": str(eq.index[train_end].date()),
                "test_start": str(eq.index[test_start].date()),
                "test_end": str(eq.index[test_end].date()),
                "test_strategy_cagr": cagr(test_eq),
                "test_benchmark_cagr": cagr(test_be),
                "test_excess": cagr(test_eq)-cagr(test_be),
            })
        return {"windows": windows, "count": len(windows)}
    except Exception as e:
        return {"error": str(e), "windows": []}
