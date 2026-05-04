"""Tool for parsing and validating incoming claim JSON."""

import json

from strands import tool

REQUIRED_FIELDS = [
    "claim_id", "policy_id", "claimant_name", "loss_date", "filed_date",
    "claim_amount", "property_address", "property_type", "cause_of_loss",
    "description", "state",
]


@tool
def parse_claim_json(claim_json: str) -> str:
    """Parse a claim JSON string and validate that all required fields are present.

    Args:
        claim_json: A JSON string containing the claim data.

    Returns:
        A formatted summary of the parsed claim, or an error message.
    """
    try:
        data = json.loads(claim_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON — {e}"

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return f"Error: Missing required fields: {', '.join(missing)}"

    lines = [f"Parsed claim {data['claim_id']}:"]
    for field in REQUIRED_FIELDS:
        value = data[field]
        if field == "claim_amount":
            value = f"${value:,.2f}"
        lines.append(f"  {field}: {value}")

    return "\n".join(lines)
