"""Tools for web-searching a claimant and storing evidence in the database."""

import os
import sqlite3
from datetime import datetime, timezone

from strands import tool
from strands_tools.tavily import tavily_search

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "claims_review.db")


@tool
def store_evidence(
    claim_id: str,
    search_query: str,
    result_summary: str,
    source_url: str,
) -> str:
    """Store web search evidence in the database for audit trail.

    Args:
        claim_id: The claim this evidence relates to.
        search_query: The search query that was run.
        result_summary: Summary of what was found.
        source_url: URL of the source (or 'N/A' if not applicable).

    Returns:
        Confirmation that evidence was stored.
    """
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO search_evidence (claim_id, search_query, result_summary, source_url, searched_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (claim_id, search_query, result_summary, source_url, now),
        )
        conn.commit()

    return f"Evidence stored for claim {claim_id}."
