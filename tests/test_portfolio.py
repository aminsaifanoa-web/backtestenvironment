from btfi.portfolio.accounting import Portfolio

def test_weighting_and_costs():
    p = Portfolio(initial_capital=10000, transaction_cost_bps=10, slippage_bps=5)
    prices = {"AAPL": 100, "MSFT": 200}
    target = {"AAPL": 0.5, "MSFT": 0.5}
    p.rebalance_to_target(target, prices, None)
    # check holdings roughly equal value
    mv_a = p.holdings.get("AAPL",0)*100
    mv_m = p.holdings.get("MSFT",0)*200
    # allow for costs
    assert abs(mv_a - mv_m) < 100
    assert p.cash >= 0

def test_sell():
    p = Portfolio(initial_capital=10000)
    p.rebalance_to_target({"AAPL":1.0}, {"AAPL":100}, None)
    # now rebalance to MSFT only
    p.rebalance_to_target({"MSFT":1.0}, {"MSFT":200, "AAPL":100}, None)
    assert "AAPL" not in p.holdings or p.holdings["AAPL"]==0
    assert p.holdings.get("MSFT",0) > 0
