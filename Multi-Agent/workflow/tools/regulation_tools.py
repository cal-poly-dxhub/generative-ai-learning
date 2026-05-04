"""Tool for querying state insurance regulations via Bedrock KB or stub fallback."""

import os
from datetime import datetime

import boto3
from strands import tool

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")
MODEL_ARN = os.environ.get(
    "BEDROCK_MODEL_ARN",
    "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
)

STUB_REGULATIONS = {
    "CA": {
        "fire": (
            "California Fair Claims Settlement Practices Regulations (Title 10, Ch. 5, Subch. 7.5):\n"
            "- Insurer must acknowledge receipt of claim within 15 calendar days.\n"
            "- Investigation must be completed within 40 calendar days of proof of claim.\n"
            "- Payment must be made within 30 calendar days after determination of liability.\n"
            "- Written notice required if claim is denied, with specific reasons cited.\n"
            "- Dwelling fire coverage must include debris removal costs.\n"
            "- Policyholder entitled to 24-month replacement/rebuild period.\n"
            "- CA Insurance Code 10089.5: ACV calculations must account for labor costs at replacement value."
        ),
        "water_damage": (
            "California Fair Claims Settlement Practices Regulations:\n"
            "- Same 15/40/30 day acknowledgment/investigation/payment deadlines apply.\n"
            "- Water damage from burst pipes covered under standard commercial property policies.\n"
            "- Mold resulting from water damage may be excluded — check policy exclusions.\n"
            "- Insurer must provide written explanation of any depreciation applied."
        ),
        "default": (
            "California Department of Insurance general requirements:\n"
            "- All claims must be processed within 40 calendar days.\n"
            "- 15-day acknowledgment window from date of filing.\n"
            "- Written denial with specific reasons required.\n"
            "- Policyholder may file complaint with CDI if deadlines are missed."
        ),
    },
    "TX": {
        "default": (
            "Texas Insurance Code Chapter 542 — Prompt Payment of Claims:\n"
            "- Insurer must acknowledge claim within 15 business days.\n"
            "- Accept or reject within 15 business days of receiving all items.\n"
            "- Payment within 5 business days of acceptance.\n"
            "- 18% annual penalty interest for late payment.\n"
            "- Written denial must include specific reasons and policy provisions."
        ),
    },
    "default": (
        "NAIC Unfair Trade Practices Act (Model Law 880) general guidelines:\n"
        "- Timely acknowledgment of claims communications.\n"
        "- Prompt investigation and fair settlement.\n"
        "- Written denial with reasons when claims are rejected.\n"
        "- No misrepresentation of policy provisions."
    ),
}


def _stub_lookup(state: str, cause_of_loss: str) -> str:
    state_regs = STUB_REGULATIONS.get(state, None)
    if state_regs is None:
        return STUB_REGULATIONS["default"]
    if isinstance(state_regs, str):
        return state_regs
    return state_regs.get(cause_of_loss, state_regs.get("default", STUB_REGULATIONS["default"]))


def _bedrock_kb_query(query: str, state: str) -> str:
    client = boto3.client("bedrock-agent-runtime", region_name="us-west-2")
    response = client.retrieve_and_generate(
        input={"text": f"For {state} insurance regulations: {query}"},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                "modelArn": MODEL_ARN,
            },
        },
    )
    return response["output"]["text"]


@tool
def query_regulations(query: str, state: str) -> str:
    """Query insurance regulations for a specific state.

    If KNOWLEDGE_BASE_ID is set, queries an Amazon Bedrock Knowledge Base.
    Otherwise falls back to built-in regulation summaries.

    Args:
        query: The regulation question (e.g. 'filing deadline for fire claims').
        state: Two-letter state code (e.g. 'CA', 'TX').

    Returns:
        Relevant regulation text for the state.
    """
    if KNOWLEDGE_BASE_ID:
        try:
            return _bedrock_kb_query(query, state)
        except Exception as e:
            return f"Bedrock KB query failed ({e}). Falling back to built-in data.\n\n{_stub_lookup(state, query)}"

    return _stub_lookup(state, query)
