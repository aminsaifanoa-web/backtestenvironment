import pandas as pd
from btfi.strategies.formula import safe_eval_formula, validate_formula, FormulaError
import pytest

def test_valid_formula():
    df = pd.DataFrame({"fcf_yield":[0.1,0.2,0.3], "roic":[0.05,0.1,0.15]})
    res = safe_eval_formula("0.5*rank(fcf_yield)+0.5*rank(roic)", df)
    assert len(res)==3

def test_invalid_function():
    df = pd.DataFrame({"a":[1,2,3]})
    with pytest.raises(FormulaError):
        safe_eval_formula("__import__('os').system('x')", df)

def test_unknown_variable():
    df = pd.DataFrame({"a":[1,2,3]})
    with pytest.raises(FormulaError):
        safe_eval_formula("rank(unknown_var)", df)

def test_validate():
    ok, msg = validate_formula("rank(fcf_yield)", ["fcf_yield","roic"])
    assert ok
    ok2, _ = validate_formula("rank(bad)", ["fcf_yield"])
    assert not ok2

def test_no_exec():
    df = pd.DataFrame({"fcf_yield":[1,2,3]})
    # attempt exec-like
    with pytest.raises(FormulaError):
        safe_eval_formula("exec('import os')", df)
