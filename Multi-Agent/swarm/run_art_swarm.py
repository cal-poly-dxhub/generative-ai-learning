#!/usr/bin/env python3
"""Collaborative Art Generator — Swarm pattern demo.

17 agents with distinct personas collaboratively brainstorm, research, draft,
critique, and produce artwork from a single prompt. The art director has final
authority — approving, rejecting, or redirecting work — and the shipper agent
produces final deliverables.

Run:
  python run_art_swarm.py
  python run_art_swarm.py "Bread"
  python run_art_swarm.py "The feeling of time passing in an empty room"
"""

import json
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.multiagent import Swarm

from strands_tools.tavily import tavily_search
from strands_tools import calculator as calculator_mod
from strands_tools import current_time as current_time_mod
from strands_tools import python_repl as python_repl_mod
from strands_tools import generate_image as generate_image_mod
from strands_tools import file_write as file_write_mod
from strands_tools import image_reader as image_reader_mod

from tools import generate_draft_image, generate_ascii_png, generate_svg_png, generate_bitmap, list_artwork_files
from agents.prompts import (
    TOPIC_REFINER_PROMPT,
    ARTIST_PROMPT, HISTORIAN_PROMPT, PHILOSOPHER_PROMPT,
    SCIENTIST_PROMPT, STORYTELLER_PROMPT, GOVERNOR_PROMPT,
    GENERAL_PROMPT, EDUCATOR_PROMPT, FARMER_PROMPT,
    DOCTOR_PROMPT, BAKER_PROMPT, ART_CRITIC_PROMPT,
    ARCHITECT_PROMPT,
    RESEARCHER_PROMPT, CANVAS_PROMPT,
    ART_DIRECTOR_PROMPT, SHIPPER_PROMPT,
    IDEATION_RULES,
)

# ── Pretty printing ─────────────────────────────────────────────────────────

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
ITALIC = "\033[3m"
RESET = "\033[0m"


TOOL_LOG = {}


class SwarmCallbackHandler:
    """Streams agent reasoning, tool calls, and responses to the terminal."""

    def __init__(self, agent_name=""):
        self.tool_count = 0
        self.tool_names = []
        self._in_reasoning = False
        self._in_text = False
        self.agent_name = agent_name
        self._current_tool = None
        self._tool_input_buf = ""

    def __call__(self, **kwargs):
        reasoning_text = kwargs.get("reasoningText", "")
        data = kwargs.get("data", "")
        complete = kwargs.get("complete", False)
        event = kwargs.get("event", {})

        tool_use_start = event.get("contentBlockStart", {}).get("start", {}).get("toolUse")
        tool_input_delta = (
            event.get("contentBlockDelta", {}).get("delta", {}).get("toolUse", {}).get("input", "")
        )
        block_stop = event.get("contentBlockStop")

        if reasoning_text:
            if not self._in_reasoning:
                print(f"      {DIM}{ITALIC}Thinking: ", end="", flush=True)
                self._in_reasoning = True
            print(f"{DIM}{ITALIC}{reasoning_text}{RESET}", end="", flush=True)

        if tool_use_start:
            if self._in_reasoning:
                print(RESET)
                self._in_reasoning = False
            if self._in_text:
                print()
                self._in_text = False
            name = tool_use_start['name']
            self.tool_count += 1
            self.tool_names.append(name)
            if self.agent_name:
                TOOL_LOG.setdefault(self.agent_name, []).append(name)

            self._current_tool = name
            self._tool_input_buf = ""

            if name != "handoff_to_agent":
                print(f"      {MAGENTA}↳ Tool: {name}{RESET}", flush=True)

        if tool_input_delta and self._current_tool == "handoff_to_agent":
            self._tool_input_buf += tool_input_delta

        if block_stop is not None and self._current_tool == "handoff_to_agent":
            target = ""
            try:
                parsed = json.loads(self._tool_input_buf)
                target = parsed.get("agent_name", "")
            except (json.JSONDecodeError, TypeError):
                pass
            if target:
                print(
                    f"      {MAGENTA}↳ Handoff: {YELLOW}{self.agent_name}{MAGENTA} → "
                    f"{YELLOW}{target}{RESET}",
                    flush=True,
                )
            else:
                print(f"      {MAGENTA}↳ Tool: handoff_to_agent{RESET}", flush=True)
            self._current_tool = None
            self._tool_input_buf = ""

        if data:
            if self._in_reasoning:
                print(RESET)
                self._in_reasoning = False
            if not self._in_text:
                print(f"      {DIM}", end="", flush=True)
                self._in_text = True
            print(data, end="", flush=True)

        if complete:
            if self._in_reasoning:
                print(RESET)
                self._in_reasoning = False
            if self._in_text:
                print(RESET)
                self._in_text = False


# ── Build agents ─────────────────────────────────────────────────────────────

def build_swarm():
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        max_tokens=4096,
    )
    opus_model = BedrockModel(
        model_id="us.anthropic.claude-opus-4-6-v1",
        max_tokens=8192,
    )

    handler = SwarmCallbackHandler

    topic_refiner = Agent(
        name="topic_refiner",
        model=model,
        system_prompt=TOPIC_REFINER_PROMPT,
        description="Receives raw user input and distills it into a clean creative brief.",
        callback_handler=handler(agent_name="topic_refiner"),
    )

    creative_personas = [
        ("artist", ARTIST_PROMPT, "Visual artist — thinks in color, form, texture, composition."),
        ("historian", HISTORIAN_PROMPT, "Historian — anchors art in historical context and time."),
        ("philosopher", PHILOSOPHER_PROMPT, "Philosopher — focuses on meaning, paradox, and duality."),
        ("scientist", SCIENTIST_PROMPT, "Scientist — finds beauty in natural structures and phenomena."),
        ("storyteller", STORYTELLER_PROMPT, "Storyteller — thinks in narrative, character, and scene."),
        ("governor", GOVERNOR_PROMPT, "Governor — sees art as public discourse and civic meaning."),
        ("general", GENERAL_PROMPT, "General — brings tension, hierarchy, and strategic composition."),
        ("educator", EDUCATOR_PROMPT, "Educator — emphasizes legibility, layered meaning, invitation."),
        ("farmer", FARMER_PROMPT, "Farmer — brings earthiness, seasons, and deep time."),
        ("doctor", DOCTOR_PROMPT, "Doctor — brings clinical precision and profound empathy."),
        ("baker", BAKER_PROMPT, "Baker — brings warmth, transformation, and craft dignity."),
        ("art_critic", ART_CRITIC_PROMPT, "Art critic — challenges, sharpens, and elevates concepts."),
        ("architect", ARCHITECT_PROMPT, "Architect — brings spatial experience, structure, and place."),
    ]

    creative_agents = []
    for name, prompt, desc in creative_personas:
        creative_agents.append(Agent(
            name=name,
            model=model,
            system_prompt=prompt + "\n\n" + IDEATION_RULES,
            description=desc,
            callback_handler=handler(agent_name=name),
        ))

    researcher = Agent(
        name="researcher",
        model=model,
        system_prompt=RESEARCHER_PROMPT,
        tools=[tavily_search, calculator_mod, current_time_mod],
        description="Enriches concepts with factual research, cultural references, and data.",
        callback_handler=handler(agent_name="researcher"),
    )

    canvas_tools = [
        python_repl_mod, generate_draft_image, file_write_mod,
        generate_ascii_png, generate_svg_png, generate_bitmap, list_artwork_files,
    ]

    canvas = Agent(
        name="canvas",
        model=model,
        system_prompt=CANVAS_PROMPT,
        tools=canvas_tools,
        description="Art director's private drafting studio. Produces visual drafts for review.",
        callback_handler=handler(agent_name="canvas"),
    )

    art_director = Agent(
        name="art_director",
        model=opus_model,
        system_prompt=ART_DIRECTOR_PROMPT,
        tools=[image_reader_mod],
        description="Senior creative authority. Reviews ideas, commissions and inspects drafts, approves for shipping.",
        callback_handler=handler(agent_name="art_director"),
    )

    shipper_tools = [
        generate_image_mod, file_write_mod,
        generate_ascii_png, generate_svg_png, generate_bitmap, list_artwork_files,
    ]

    shipper = Agent(
        name="shipper",
        model=opus_model,
        system_prompt=SHIPPER_PROMPT,
        tools=shipper_tools,
        description="Final production. Generates polished artwork in selected media formats.",
        callback_handler=handler(agent_name="shipper"),
    )

    all_agents = [
        topic_refiner,
        *creative_agents,
        researcher,
        canvas,
        art_director,
        shipper,
    ]

    swarm = Swarm(
        nodes=all_agents,
        entry_point=topic_refiner,
        max_handoffs=25,
        max_iterations=30,
        execution_timeout=600.0,
        node_timeout=300.0,
    )

    return swarm


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Collaborative Art Generator — 17-agent swarm demo"
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Creative prompt for the swarm (e.g. 'Bread', 'The feeling of time passing')",
    )
    args = parser.parse_args()

    if args.prompt:
        prompt = args.prompt
    else:
        prompt = input(f"\n  {BOLD}Enter a creative prompt:{RESET} ").strip()
        if not prompt:
            prompt = "The feeling of time passing in an empty room"
            print(f"  {DIM}Using default: {prompt}{RESET}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "drafts"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "output"), exist_ok=True)

    print(f"\n{CYAN}{'━' * 70}{RESET}")
    print(f"  {BOLD}SWARM PATTERN DEMO — Collaborative Art Generator{RESET}")
    print(f"{CYAN}{'━' * 70}{RESET}")
    print(f"  {DIM}Prompt: {prompt}{RESET}")
    print()
    print(f"  {DIM}17 agents: 1 refiner + 13 creative personas + 1 researcher + 1 canvas + 1 art director + 1 shipper{RESET}")
    print(f"  {DIM}Handoff path is emergent — agents self-organize based on the concept.{RESET}")
    print()

    swarm = build_swarm()
    t0 = time.time()
    result = swarm(prompt)
    elapsed = time.time() - t0

    # ── Execution Summary ────────────────────────────────────────────────
    print(f"\n{CYAN}{'━' * 70}{RESET}")
    print(f"  {BOLD}Execution Summary{RESET}")
    print(f"{CYAN}{'━' * 70}{RESET}")
    print(f"  Status       : {GREEN}{result.status}{RESET}")

    history = [n.node_id for n in result.node_history]
    chain = ""
    for i, agent_name in enumerate(history):
        if i > 0:
            chain += f" {MAGENTA}→{RESET} "
        chain += f"{YELLOW}{agent_name}{RESET}"
    print(f"  Agent path   : {chain}")
    print(f"  Handoffs     : {len(history) - 1}")
    print(f"  Time         : {elapsed:.1f}s")

    print(f"\n  {BOLD}Agent contributions:{RESET}")
    for node in result.node_history:
        r = result.results.get(node.node_id)
        if r and r.result:
            text = str(r.result)[:200].replace("\n", " ").strip()
            print(f"    {YELLOW}{node.node_id:18}{RESET}: {DIM}{text}...{RESET}")

    if TOOL_LOG:
        total_tools = sum(len(v) for v in TOOL_LOG.values())
        print(f"\n  {BOLD}Tools invoked ({total_tools} total):{RESET}")
        for agent_name in history:
            tools = TOOL_LOG.get(agent_name, [])
            if tools:
                tool_str = ", ".join(tools)
                print(f"    {YELLOW}{agent_name:18}{RESET}: {MAGENTA}{tool_str}{RESET}")

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    if os.path.isdir(output_dir) and os.listdir(output_dir):
        print(f"\n  {BOLD}Output files:{RESET}")
        for f in sorted(os.listdir(output_dir)):
            fpath = os.path.join(output_dir, f)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                print(f"    {GREEN}{f}{RESET} ({size:,} bytes)")

    # ── Trace Log ────────────────────────────────────────────────────────
    trace_path = save_trace_log(prompt, result, elapsed)
    print(f"\n  {BOLD}Trace log:{RESET}")
    print(f"    {GREEN}{trace_path}{RESET}")

    print(f"\n{CYAN}{'━' * 70}{RESET}\n")


def save_trace_log(prompt, result, elapsed):
    """Serialize the full swarm execution trace to a JSON file in ./traces/."""
    traces_dir = os.path.join(os.path.dirname(__file__), "traces")
    os.makedirs(traces_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = "_".join(prompt.lower().split()[:4])[:30]
    filename = f"{timestamp}_{slug}.json"

    history = [n.node_id for n in result.node_history]

    trace = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "status": str(result.status),
        "elapsed_seconds": round(elapsed, 2),
        "agent_path": history,
        "handoffs": len(history) - 1,
        "accumulated_usage": dict(result.accumulated_usage),
        "accumulated_metrics": dict(result.accumulated_metrics),
        "execution_count": result.execution_count,
        "tools_invoked": dict(TOOL_LOG),
        "agents": {},
    }

    for node in result.node_history:
        node_result = result.results.get(node.node_id)
        if not node_result:
            continue

        agent_entry = {
            "status": str(node_result.status),
            "execution_time_ms": node_result.execution_time,
            "accumulated_usage": dict(node_result.accumulated_usage),
            "tools_called": TOOL_LOG.get(node.node_id, []),
        }

        agent_result = node_result.result
        if hasattr(agent_result, "metrics"):
            metrics = agent_result.metrics
            summary = metrics.get_summary()
            agent_entry["cycle_count"] = summary["total_cycles"]
            agent_entry["total_duration"] = round(summary["total_duration"], 3)
            agent_entry["avg_cycle_time"] = round(summary["average_cycle_time"], 3)
            agent_entry["cycle_durations"] = [round(d, 3) for d in metrics.cycle_durations]
            agent_entry["tool_metrics"] = {
                name: {
                    "call_count": tm["execution_stats"]["call_count"],
                    "success_count": tm["execution_stats"]["success_count"],
                    "error_count": tm["execution_stats"]["error_count"],
                    "total_time": round(tm["execution_stats"]["total_time"], 3),
                    "avg_time": round(tm["execution_stats"]["average_time"], 3),
                }
                for name, tm in summary["tool_usage"].items()
            }
            agent_entry["traces"] = summary["traces"]
            agent_entry["agent_invocations"] = summary["agent_invocations"]
            agent_entry["response"] = str(agent_result)[:500]

        trace["agents"][node.node_id] = agent_entry

    trace_path = os.path.join(traces_dir, filename)
    with open(trace_path, "w") as f:
        json.dump(trace, f, indent=2, default=str)

    return trace_path


if __name__ == "__main__":
    main()
