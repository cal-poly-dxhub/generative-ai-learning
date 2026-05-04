"""Tools for calculating payouts and storing final verdicts."""

import ast
import operator
import os
import sqlite3
from datetime import datetime, timezone

from strands import tool

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "claims_review.db")

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPERATORS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return SAFE_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPERATORS:
        return SAFE_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


@tool
def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression and return the result.

    Supports +, -, *, / and parentheses with numeric values only.

    Args:
        expression: A math expression (e.g. '185000 * (1 - 0.03 * 12)').

    Returns:
        The numeric result as a string.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return f"{result:,.2f}"
    except Exception as e:
        return f"Calculation error: {e}"


@tool
def store_verdict(
    claim_id: str,
    verdict: str,
    approved_amount: float,
    coverage_result: str,
    regulation_result: str,
    fraud_result: str,
    payout_calculation: str,
    reasoning: str,
) -> str:
    """Store the final compliance verdict in the database.

    Args:
        claim_id: The claim being reviewed.
        verdict: One of APPROVED, DENIED, or FLAGGED_FOR_REVIEW.
        approved_amount: The approved payout amount (0 if denied).
        coverage_result: Summary of coverage check findings.
        regulation_result: Summary of regulation check findings.
        fraud_result: Summary of fraud screening findings.
        payout_calculation: Summary of payout calculation.
        reasoning: Full reasoning for the verdict.

    Returns:
        Confirmation that the verdict was stored.
    """
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO verdicts (claim_id, verdict, approved_amount, coverage_result, "
            "regulation_result, fraud_result, payout_calculation, reasoning, reviewed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (claim_id, verdict, approved_amount, coverage_result,
             regulation_result, fraud_result, payout_calculation, reasoning, now),
        )
        conn.commit()

    return f"Verdict stored for claim {claim_id}: {verdict} — ${approved_amount:,.2f}"
