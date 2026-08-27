from __future__ import annotations

# Quantitative verdict rules (transparent, no LLM)
# Possible verdicts:
# - BUY THE FUCKING INDEX
# - ACTUALLY FUCKING WORKS
# - INTERESTING, BUT NOT ROBUST
# - FUCKED BY COSTS
# - DATA TOO SHITTY TO KNOW

def compute_verdict(metrics: dict, rolling_5y: dict, param_robust: list[dict], cost_robust: list[dict], warnings: list[str]) -> tuple[str, str, dict]:
    """
    Returns (verdict, reason, score_components)
    """
    excess = metrics.get("excess_cagr", 0) or 0
    sharpe = metrics.get("sharpe", 0) or 0
    mdd = metrics.get("max_drawdown", 0) or 0
    win_rate_5y = rolling_5y.get("win_rate", 0) if rolling_5y and "win_rate" in rolling_5y else 0

    # Data quality check
    if metrics.get("cagr") is None or abs(metrics.get("cagr",0))==0 and metrics.get("total_return",0)==0:
        return "DATA TOO SHITTY TO KNOW", "Insufficient data to compute meaningful returns.", {"excess": excess}

    # Cost robustness: does excess survive at 100 bps?
    cost_survives = True
    if cost_robust:
        gross = next((r["excess"] for r in cost_robust if r.get("cost_bps")==0), excess)
        high_cost = next((r["excess"] for r in cost_robust if r.get("cost_bps")==100), None)
        if high_cost is not None and high_cost < 0.005 and gross > 0.01:
            # Gross positive but high cost flips negative or trivial
            cost_survives = False

    # Parameter robustness: what fraction of nearby params beat benchmark?
    param_beats = 0
    param_total = 0
    for r in param_robust or []:
        if "excess" in r and r["excess"] is not None:
            param_total += 1
            if r["excess"] > 0:
                param_beats += 1
    param_win_rate = param_beats/param_total if param_total else 1.0

    # Score components 0-100 each then weighted
    # Excess CAGR: 5%+ = 100, 0% =0, -2% =0
    excess_score = max(0, min(100, (excess*100) * 20))  # 5% => 100
    sharpe_score = max(0, min(100, sharpe*50))  # sharpe 2 => 100
    drawdown_score = max(0, min(100, 100 - abs(mdd)*200))  # -10% => 80, -50% => 0
    win_rate_score = (win_rate_5y or 0)*100
    param_score = param_win_rate*100
    cost_score = 100 if cost_survives else 20

    btfi_score = round(0.30*excess_score + 0.15*sharpe_score + 0.15*drawdown_score + 0.15*win_rate_score + 0.15*param_score + 0.10*cost_score, 1)
    components = {
        "excess_cagr": round(float(excess*100),2),
        "excess_score": round(excess_score,1),
        "sharpe": round(float(sharpe),2),
        "sharpe_score": round(sharpe_score,1),
        "max_drawdown": round(float(mdd*100),2),
        "drawdown_score": round(drawdown_score,1),
        "win_rate_5y": round(float(win_rate_5y*100),1) if win_rate_5y else 0,
        "win_rate_score": round(win_rate_score,1),
        "param_win_rate": round(param_win_rate*100,1),
        "param_score": round(param_score,1),
        "cost_survives": cost_survives,
        "cost_score": cost_score,
        "btfi_score": btfi_score,
    }

    # Verdict logic
    if not cost_survives and excess > 0.01:
        return "FUCKED BY COSTS", f"Gross excess {excess*100:.1f}% disappears after realistic costs (100 bps).", components
    if excess < 0.005 and win_rate_5y is not None and win_rate_5y < 0.5:
        # check if data warnings heavy
        if warnings and len([w for w in warnings if "look-ahead" in w.lower() or "survivorship" in w.lower()]) >= 1 and excess < 0.01:
            # still BFIndex but flag data
            pass
        return "BUY THE FUCKING INDEX", f"Excess CAGR {excess*100:.2f}% with 5Y win rate {win_rate_5y*100:.0f}% does not justify abandoning the index.", components
    if excess > 0.02 and win_rate_5y and win_rate_5y > 0.65 and param_win_rate > 0.6 and sharpe > 0.6 and btfi_score > 60:
        return "ACTUALLY FUCKING WORKS", f"Substantial excess {excess*100:.1f}% with robust win rate {win_rate_5y*100:.0f}% and parameter stability.", components
    if excess > 0.01 and (win_rate_5y < 0.6 or param_win_rate < 0.6 or btfi_score < 50):
        return "INTERESTING, BUT NOT ROBUST", f"Excess {excess*100:.1f}% but depends on specific dates/params (win {win_rate_5y*100:.0f}%, param {param_win_rate*100:.0f}%).", components
    if btfi_score < 30 or excess < -0.01:
        return "BUY THE FUCKING INDEX", f"Negative or negligible risk-adjusted edge (BTFI score {btfi_score}).", components
    # default
    if excess > 0.01 and btfi_score >= 50:
        return "ACTUALLY FUCKING WORKS", f"Meets robustness thresholds with BTFI score {btfi_score}.", components
    return "BUY THE FUCKING INDEX", f"Does not demonstrate sufficiently robust outperformance (excess {excess*100:.2f}%, score {btfi_score}).", components
