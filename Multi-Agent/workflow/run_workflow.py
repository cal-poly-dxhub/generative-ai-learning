#!/usr/bin/env python3
"""Insurance Claim Compliance Review — 6-agent sequential workflow.

Demonstrates the Strands Workflow pattern: agents chained in code with
explicit input/output passing. Each agent has its own tools and system prompt.

Pipeline:
  1. Extract Claim Data
  2. Policy Coverage Check
  3. State Regulation Check
  4. Fraud Screening
  5. Calculate Payout
  6. Compile Verdict

Run:
  python setup_db.py          # Create and seed the database (once)
  python run_workflow.py       # Run the full pipeline
  python run_workflow.py --claim data/other_claim.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from strands import Agent
from strands.models.bedrock import BedrockModel

from tools import (
    parse_claim_json,
    insert_claim,
    query_db,
    query_regulations,
    store_evidence,
    calculate,
    store_verdict,
)
from strands_tools.tavily import tavily_search

# ── Pretty printing helpers ─────────────────────────────────────────────────

GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
ITALIC = "\033[3m"
RESET = "\033[0m"

INDENT = "    "

TOOL_LOG = {}


class WorkflowCallbackHandler:
    """Streams agent reasoning, tool calls, and responses to the terminal."""

    def __init__(self, step_name=""):
        self.tool_count = 0
        self.tool_names = []
        self._in_reasoning = False
        self._in_text = False
        self.step_name = step_name

    def __call__(self, **kwargs):
        reasoning_text = kwargs.get("reasoningText", "")
        data = kwargs.get("data", "")
        complete = kwargs.get("complete", False)
        event = kwargs.get("event", {})

        tool_use = event.get("contentBlockStart", {}).get("start", {}).get("toolUse")

        if reasoning_text:
            if not self._in_reasoning:
                print(f"\n{INDENT}{DIM}{ITALIC}Thinking: ", end="", flush=True)
                self._in_reasoning = True
            print(f"{DIM}{ITALIC}{reasoning_text}{RESET}", end="", flush=True)

        if tool_use:
            if self._in_reasoning:
                print(RESET)
                self._in_reasoning = False
            if self._in_text:
                print()
                self._in_text = False
            name = tool_use['name']
            self.tool_count += 1
            self.tool_names.append(name)
            if self.step_name:
                TOOL_LOG.setdefault(self.step_name, []).append(name)
            print(f"{INDENT}{MAGENTA}  ↳ Tool #{self.tool_count}: {name}{RESET}", flush=True)

        if data:
            if self._in_reasoning:
                print(RESET)
                self._in_reasoning = False
            if not self._in_text:
                print(f"{INDENT}{DIM}", end="", flush=True)
                self._in_text = True
            print(data, end="", flush=True)

        if complete:
            if self._in_reasoning:
                print(RESET)
                self._in_reasoning = False
            if self._in_text:
                print(RESET)
                self._in_text = False


def header(claim_path):
    print(f"\n{GREEN}{'━' * 70}{RESET}")
    print(f"  {BOLD}WORKFLOW PATTERN DEMO — Insurance Claim Compliance Review{RESET}")
    print(f"{GREEN}{'━' * 70}{RESET}")
    print(f"{DIM}  Claim file: {claim_path}{RESET}")
    print()
    print(f"  {DIM}Pipeline (deterministic, sequential):{RESET}")
    print(f"  {DIM}  1. Extract → 2. Coverage → 3. Regulation → 4. Fraud → 5. Payout → 6. Verdict{RESET}")
    print()


def step_start(num, total, name, description):
    print(f"\n  {YELLOW}▶ Step {num}/{total}: {name}{RESET}")
    print(f"  {DIM}  {description}{RESET}")


def step_done(num, name, elapsed):
    print(f"\n  {GREEN}✓ Step {num}: {name} done{RESET} ({elapsed:.1f}s)")
    print()


# ── Agent definitions ───────────────────────────────────────────────────────

def create_model():
    return BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        max_tokens=4096,
    )


AGENTS = [
    {
        "name": "Extract Claim Data",
        "description": "Parse claim JSON → insert structured data into SQLite",
        "tools": [parse_claim_json, insert_claim],
        "system_prompt": (
            "You are a claims intake specialist. Your job is to parse the incoming "
            "insurance claim data and store it in the database.\n\n"
            "Steps:\n"
            "1. Use parse_claim_json to validate the claim JSON string.\n"
            "2. If valid, use insert_claim with all the extracted fields.\n"
            "3. Report a brief summary of the claim you just ingested."
        ),
    },
    {
        "name": "Policy Coverage Check",
        "description": "Query SQLite for policy terms → check coverage, limits, dates",
        "tools": [query_db],
        "system_prompt": (
            "You are a policy compliance analyst. Verify that the claim falls within "
            "the policy's coverage terms.\n\n"
            "Steps:\n"
            "1. Query the policies table for the policy_id from the claim.\n"
            "2. Check: Is the policy active on the loss date? (loss_date between effective_date and expiration_date)\n"
            "3. Check: Is the cause_of_loss listed in covered_perils?\n"
            "4. Check: Is the cause_of_loss in the exclusions list?\n"
            "5. Check: Does the claimed amount exceed the coverage_limit?\n\n"
            "Report your findings as: COVERED, NOT_COVERED, or PARTIAL — with specific reasons."
        ),
    },
    {
        "name": "State Regulation Check",
        "description": "RAG query to regulations KB → check claim against state rules",
        "tools": [query_db, query_regulations],
        "system_prompt": (
            "You are a regulatory compliance specialist. Check the claim against "
            "state-specific insurance regulations.\n\n"
            "Steps:\n"
            "1. Query the claims table to get the claim's state, loss_date, filed_date, and cause_of_loss.\n"
            "2. Use query_regulations to look up applicable regulations for that state.\n"
            "3. Check: Was the claim filed within the state's required timeframe?\n"
            "4. Check: Are there state-mandated procedures that apply?\n"
            "5. Check: Are there settlement practice requirements?\n\n"
            "Report: COMPLIANT or NON_COMPLIANT with specific regulation citations."
        ),
    },
    {
        "name": "Fraud Screening",
        "description": "Query claim history + web search → flag red flags",
        "tools": [query_db, tavily_search, store_evidence],
        "system_prompt": (
            "You are a fraud detection analyst. Screen the claim for red flags.\n\n"
            "Steps:\n"
            "1. Query the claim_history table for prior claims by this claimant/policy.\n"
            "2. Analyze: claim frequency, escalating amounts, suspicious patterns.\n"
            "3. Query the claims table for the current claim amount and policy details from policies table.\n"
            "4. Calculate claim-to-property-value ratio.\n"
            "5. Check timing: is the loss date suspiciously close to policy inception or expiration?\n"
            "6. Use tavily_search to search the web for the claimant's name and location.\n"
            "7. Use store_evidence to save the search results for the audit trail.\n\n"
            "Report: LOW, MEDIUM, or HIGH risk with a list of specific findings. "
            "Be factual — flag concerns, don't make accusations."
        ),
    },
    {
        "name": "Calculate Payout",
        "description": "Pull policy terms + claim data → compute payout with all adjustments",
        "tools": [query_db, calculate],
        "system_prompt": (
            "You are a financial analyst specializing in insurance claims. Calculate "
            "the expected payout using policy terms.\n\n"
            "Steps:\n"
            "1. Query the policies table for: deductible, coinsurance_pct, coverage_limit, "
            "property_value, depreciation_rate, property_age_years.\n"
            "2. Query the claims table for: claim_amount.\n"
            "3. Calculate depreciation: depreciated_value = claim_amount * (1 - depreciation_rate * property_age_years)\n"
            "4. Check coinsurance: required_coverage = property_value * coinsurance_pct. "
            "If coverage_limit >= required_coverage, no penalty. Otherwise penalty = coverage_limit / required_coverage.\n"
            "5. Apply penalty: adjusted = depreciated_value * coinsurance_penalty\n"
            "6. Subtract deductible: payout = adjusted - deductible\n"
            "7. Cap at coverage_limit: payout = min(payout, coverage_limit)\n"
            "8. Floor at zero: payout = max(payout, 0)\n\n"
            "Use the calculate tool for each arithmetic step. Show ALL math clearly."
        ),
    },
    {
        "name": "Compile Verdict",
        "description": "Review all findings → issue APPROVED/DENIED/FLAGGED_FOR_REVIEW verdict",
        "tools": [query_db, store_verdict],
        "system_prompt": (
            "You are a senior claims compliance officer. Review all findings from the "
            "prior steps and issue a final verdict.\n\n"
            "Your verdict MUST be one of:\n"
            "- APPROVED: claim is compliant and should be paid at the calculated amount\n"
            "- DENIED: coverage issue or regulation violation prevents payment\n"
            "- FLAGGED_FOR_REVIEW: fraud concerns or edge cases requiring human review\n\n"
            "Steps:\n"
            "1. Review all the information provided from prior steps.\n"
            "2. Determine the appropriate verdict.\n"
            "3. Use store_verdict to save the decision in the database. Include summaries "
            "of each prior step's findings in the appropriate fields.\n"
            "4. Provide a clear final summary citing each step."
        ),
    },
]


# ── Workflow execution ──────────────────────────────────────────────────────

def run_workflow(claim_path: str):
    with open(claim_path) as f:
        claim_data = json.load(f)

    claim_id = claim_data["claim_id"]
    claim_json_str = json.dumps(claim_data)

    header(claim_path)

    model = create_model()
    step_times = []
    results = []
    agent_results = []

    prompts = [
        f"Parse and store this insurance claim. Here is the claim JSON:\n{claim_json_str}",

        f"Check policy coverage for claim {claim_id} (policy {claim_data['policy_id']}). "
        f"The claim is for {claim_data['cause_of_loss']} damage, amount ${claim_data['claim_amount']:,.2f}, "
        f"loss date {claim_data['loss_date']}.",

        f"Check state regulations for claim {claim_id} in state {claim_data['state']}. "
        f"Cause of loss: {claim_data['cause_of_loss']}. "
        f"Previous step (coverage check) found: {{prev}}",

        f"Screen claim {claim_id} for fraud. Claimant: {claim_data['claimant_name']}, "
        f"location: {claim_data.get('property_address', claim_data['state'])}. "
        f"Policy coverage result: {{coverage}}",

        f"Calculate the payout for claim {claim_id}. "
        f"Coverage status: {{coverage}}. Fraud assessment: {{fraud}}",

        f"Compile the final verdict for claim {claim_id}. "
        f"Coverage: {{coverage}}\nRegulations: {{regulation}}\n"
        f"Fraud screening: {{fraud}}\nPayout calculation: {{payout}}",
    ]

    for i, agent_def in enumerate(AGENTS):
        step_num = i + 1
        step_start(step_num, len(AGENTS), agent_def["name"], agent_def["description"])

        handler = WorkflowCallbackHandler(step_name=agent_def["name"])
        agent = Agent(
            model=model,
            tools=agent_def["tools"],
            system_prompt=agent_def["system_prompt"],
            callback_handler=handler,
        )

        prompt = prompts[i]
        if step_num == 3:
            prompt = prompt.format(prev=results[1])
        elif step_num == 4:
            prompt = prompt.format(coverage=results[1])
        elif step_num == 5:
            prompt = prompt.format(coverage=results[1], fraud=results[3])
        elif step_num == 6:
            prompt = prompt.format(
                coverage=results[1],
                regulation=results[2],
                fraud=results[3],
                payout=results[4],
            )

        t0 = time.time()
        result = agent(prompt)
        dt = time.time() - t0

        result_str = str(result)
        results.append(result_str)
        agent_results.append(result)
        step_times.append(dt)

        step_done(step_num, agent_def["name"], dt)

    # ── Execution summary ───────────────────────────────────────────────────
    total_time = sum(step_times)
    print(f"{GREEN}{'━' * 70}{RESET}")
    print(f"  {BOLD}Execution Summary{RESET}")
    print(f"{GREEN}{'━' * 70}{RESET}")
    print(f"  Steps completed: {GREEN}{len(AGENTS)}/{len(AGENTS)}{RESET}")
    print(f"  Total time     : {total_time:.1f}s")

    for i, (agent_def, dt) in enumerate(zip(AGENTS, step_times)):
        bar_len = int(dt / total_time * 30) if total_time > 0 else 0
        bar = "█" * bar_len + "░" * (30 - bar_len)
        print(f"    {YELLOW}{agent_def['name']:25}{RESET} {bar} {dt:.1f}s")

    if TOOL_LOG:
        total_tools = sum(len(v) for v in TOOL_LOG.values())
        print(f"\n  {BOLD}Tools invoked ({total_tools} total):{RESET}")
        for agent_def in AGENTS:
            tools = TOOL_LOG.get(agent_def["name"], [])
            if tools:
                tool_str = ", ".join(tools)
                print(f"    {YELLOW}{agent_def['name']:25}{RESET}: {MAGENTA}{tool_str}{RESET}")

    print(f"\n  {BOLD}Final Verdict:{RESET}")
    for line in results[-1].split("\n"):
        print(f"    {line}")

    trace_path = save_trace_log(claim_data, agent_results, step_times, total_time)
    print(f"\n  {BOLD}Trace log:{RESET}")
    print(f"    {GREEN}{trace_path}{RESET}")

    print(f"\n{GREEN}{'━' * 70}{RESET}\n")


# ── Trace logging ──────────────────────────────────────────────────────────

def save_trace_log(claim_data, agent_results, step_times, total_time):
    """Serialize the full workflow execution trace to a JSON file in ./traces/."""
    traces_dir = os.path.join(os.path.dirname(__file__), "traces")
    os.makedirs(traces_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    claim_id = claim_data.get("claim_id", "unknown")
    filename = f"{timestamp}_{claim_id}.json"

    steps = []
    for i, (agent_def, agent_result, dt) in enumerate(zip(AGENTS, agent_results, step_times)):
        step_entry = {
            "step": i + 1,
            "name": agent_def["name"],
            "description": agent_def["description"],
            "execution_time_seconds": round(dt, 2),
            "tools_called": TOOL_LOG.get(agent_def["name"], []),
        }

        if hasattr(agent_result, "metrics"):
            metrics = agent_result.metrics
            summary = metrics.get_summary()
            step_entry["cycle_count"] = summary["total_cycles"]
            step_entry["total_duration"] = round(summary["total_duration"], 3)
            step_entry["avg_cycle_time"] = round(summary["average_cycle_time"], 3)
            step_entry["cycle_durations"] = [round(d, 3) for d in metrics.cycle_durations]
            step_entry["tool_metrics"] = {
                name: {
                    "call_count": tm["execution_stats"]["call_count"],
                    "success_count": tm["execution_stats"]["success_count"],
                    "error_count": tm["execution_stats"]["error_count"],
                    "total_time": round(tm["execution_stats"]["total_time"], 3),
                    "avg_time": round(tm["execution_stats"]["average_time"], 3),
                }
                for name, tm in summary["tool_usage"].items()
            }
            step_entry["traces"] = summary["traces"]
            step_entry["agent_invocations"] = summary["agent_invocations"]

        step_entry["response"] = str(agent_result)[:500]
        steps.append(step_entry)

    trace = {
        "timestamp": datetime.now().isoformat(),
        "claim_id": claim_id,
        "claim_data": claim_data,
        "total_time_seconds": round(total_time, 2),
        "step_count": len(AGENTS),
        "tools_invoked": dict(TOOL_LOG),
        "steps": steps,
    }

    trace_path = os.path.join(traces_dir, filename)
    with open(trace_path, "w") as f:
        json.dump(trace, f, indent=2, default=str)

    return trace_path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Insurance Claim Compliance Review — 6-agent workflow demo"
    )
    parser.add_argument(
        "--claim",
        default=os.path.join(os.path.dirname(__file__), "data", "sample_claim.json"),
        help="Path to the claim JSON file (default: data/sample_claim.json)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.claim):
        print(f"Error: Claim file not found: {args.claim}")
        sys.exit(1)

    db_path = os.path.join(os.path.dirname(__file__), "claims_review.db")
    if not os.path.exists(db_path):
        print("Database not found. Run setup_db.py first:")
        print("  python setup_db.py")
        sys.exit(1)

    run_workflow(args.claim)


if __name__ == "__main__":
    main()
