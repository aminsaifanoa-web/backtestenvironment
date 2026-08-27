from __future__ import annotations
import ast
import pandas as pd
import numpy as np

ALLOWED_FUNCS = {"rank", "zscore", "percentile", "mean", "median", "min", "max"}
ALLOWED_OPS = {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.Gt, ast.Lt, ast.GtE, ast.LtE, ast.Eq, ast.NotEq}
ALLOWED_BOOL = {"and", "or"}

class FormulaError(Exception):
    pass

def safe_eval_formula(formula: str, df: pd.DataFrame) -> pd.Series | pd.DataFrame:
    """
    Safe formula evaluator. df: columns are metrics, rows tickers or dates?
    We support cross-sectional scoring: df columns = metrics, index = tickers
    Functions operate cross-sectionally.
    Example: 0.5*rank(fcf_yield) + 0.3*rank(roic) + 0.2*rank(momentum_12m)
    """
    # Validate AST
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Syntax error: {e}")

    # Walk and validate
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
                raise FormulaError(f"Function not allowed: {getattr(node.func, 'id', str(node.func))}. Allowed: {ALLOWED_FUNCS}")
        elif isinstance(node, ast.Name):
            if node.id not in df.columns and node.id not in ALLOWED_FUNCS and node.id not in ("and","or"):
                # allow numeric constants? names must be columns
                raise FormulaError(f"Unknown variable '{node.id}'. Available: {list(df.columns)}")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in ALLOWED_OPS:
                raise FormulaError(f"Operator not allowed: {type(node.op).__name__}")
        elif isinstance(node, ast.Compare):
            for op in node.ops:
                if type(op) not in ALLOWED_OPS:
                    raise FormulaError(f"Comparator not allowed")
        elif isinstance(node, ast.BoolOp):
            if type(node.op).__name__.lower() not in ALLOWED_BOOL:
                raise FormulaError(f"Boolean op not allowed")
        elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute, ast.Subscript)):
            raise FormulaError(f"Construct not allowed: {type(node).__name__}")

    # Prepare evaluation environment
    # Provide column vectors as Series
    env = {}
    for col in df.columns:
        env[col] = df[col]

    # Define functions operating on Series
    def rank(s):
        if isinstance(s, (int, float)):
            return s
        return s.rank(pct=False, ascending=True)

    def zscore(s):
        if isinstance(s, (int, float)):
            return s
        return (s - s.mean()) / (s.std(ddof=0) or 1)

    def percentile(s):
        if isinstance(s, (int, float)):
            return s
        return s.rank(pct=True)

    def mean_func(s):
        return s.mean() if hasattr(s, "mean") else np.mean(s)

    def median_func(s):
        return s.median() if hasattr(s, "median") else np.median(s)

    env.update({
        "rank": rank,
        "zscore": zscore,
        "percentile": percentile,
        "mean": mean_func,
        "median": median_func,
        "min": lambda s: s.min() if hasattr(s, "min") else np.min(s),
        "max": lambda s: s.max() if hasattr(s, "max") else np.max(s),
    })

    # Evaluate safely via eval with limited globals
    try:
        result = eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, env)
    except Exception as e:
        raise FormulaError(f"Evaluation error: {e}")

    return result

def validate_formula(formula: str, available_vars: list[str]) -> tuple[bool, str]:
    # create dummy df
    dummy = pd.DataFrame({v: [1.0, 2.0, 3.0] for v in available_vars})
    try:
        safe_eval_formula(formula, dummy)
        return True, "OK"
    except FormulaError as e:
        return False, str(e)
