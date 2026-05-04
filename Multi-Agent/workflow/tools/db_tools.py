"""Database tools for querying and inserting insurance claim data."""

import os
import sqlite3

from strands import tool

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "claims_review.db")


def _get_connection():
    return sqlite3.connect(DB_PATH)


@tool
def query_db(sql: str) -> str:
    """Execute a read-only SQL SELECT query against the claims database.

    Args:
        sql: A SELECT query to run against the database.

    Returns:
        Query results as formatted text, or an error message.
    """
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."

    with _get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = cursor.fetchall()

    if not rows:
        return "Query returned 0 rows."

    columns = rows[0].keys()
    lines = [" | ".join(columns)]
    lines.append("-" * len(lines[0]))
    for row in rows:
        lines.append(" | ".join(str(row[col]) for col in columns))

    return f"{len(rows)} row(s) returned:\n" + "\n".join(lines)


@tool
def insert_claim(
    claim_id: str,
    policy_id: str,
    claimant_name: str,
    loss_date: str,
    filed_date: str,
    claim_amount: float,
    property_address: str,
    property_type: str,
    cause_of_loss: str,
    description: str,
    state: str,
) -> str:
    """Insert a new claim record into the claims database.

    Args:
        claim_id: Unique claim identifier.
        policy_id: Associated policy identifier.
        claimant_name: Name of the claimant.
        loss_date: Date of the loss (ISO format).
        filed_date: Date the claim was filed (ISO format).
        claim_amount: Dollar amount claimed.
        property_address: Address of the property.
        property_type: Type of property (e.g. warehouse, office).
        cause_of_loss: What caused the loss (e.g. fire, water_damage).
        description: Description of the incident.
        state: Two-letter state code.

    Returns:
        Confirmation message.
    """
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (claim_id, policy_id, claimant_name, loss_date, filed_date,
             claim_amount, property_address, property_type, cause_of_loss,
             description, state),
        )
        conn.commit()

    return f"Claim {claim_id} inserted successfully."
