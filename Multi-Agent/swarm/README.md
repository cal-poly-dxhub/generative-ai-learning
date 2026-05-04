# Swarm Pattern: Collaborative Art Generator

17 agents with distinct creative personas collaboratively brainstorm, draft, critique, and produce artwork from a single prompt. The **swarm pattern** means the handoff path is emergent -- agents self-organize based on the concept, not a hardcoded sequence.

## Contact

- Darren Kraker - dkraker@calpoly.edu
- Nick Osterbur - nosterbu@calpoly.edu

## How the Swarm Works

```
                              YOU PROVIDE
                              ───────────
                           "The feeling of
                            time passing in
                            an empty room"
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SWARM PIPELINE                               │
│                                                                     │
│  ┌──────────────┐     ┌──────────────────────────────────────┐      │
│  │ topic_refiner│────>│  CREATIVE TEAM (13 persona agents)   │      │
│  │ distills a   │     │                                      │      │
│  │ creative     │     │  artist  historian  philosopher      │      │
│  │ brief        │     │  scientist  storyteller  governor    │      │
│  └──────┬───────┘     │  general  educator  farmer  doctor   │      │
│         │             │  baker  art_critic  architect        │      │
│         │             │                                      │      │
│         │ OR          │  Agents hand off to each other,      │      │
│         ▼             │  building a RUNNING BRIEF of ideas   │      │
│  ┌────────────┐       └──────────────┬───────────────────────┘      │
│  │ researcher │<─────────────────────┤                              │
│  │ web search,│ any creative agent   │                              │
│  │ fact-check │ can request research │                              │
│  └──────┬─────┘                      │                              │
│         │ hands back                 │                              │
│         └────────────────────────────┤                              │
│                                      │                              │
│                            ┌─────────▼──────────┐                   │
│  ┌────────────┐            │   art_director      │                  │
│  │  canvas    │<──────────>│   (Opus 4.6)        │                  │
│  │  produces  │  max 1     │                     │                  │
│  │  drafts    │  revision  │   CHECKPOINT: steer │                  │
│  └────────────┘            │   ideation back     │                  │
│                            │                     │                  │
│                            │   FINAL REVIEW:     │                  │
│                            │   synthesize into   │                  │
│                            │   PRODUCTION        │                  │
│                            │   DIRECTIVE         │                  │
│                            └─────────┬───────────┘                  │
│                                      │                              │
│                            ┌─────────▼──────────┐                   │
│                            │   shipper           │                  │
│                            │   (Opus 4.6)        │                  │
│                            │   1-3 formats,      │    YOU GET       │
│                            │   one attempt each   │    ───────      │
│                            └─────────┬───────────┘                  │
│                                      │                              │
└──────────────────────────────────────┼──────────────────────────────┘
                                       │
                              ┌────────▼────────┐
                              │   ./output/      │
                              │                  │
                              │  SD image (.png) │
                              │  ASCII art (.png)│
                              │  SVG art (.png)  │
                              │  Pixel art (.png)│
                              └─────────────────┘
```

## Agent-to-Agent Dynamics

### How Handoffs Work

There is no routing code. Strands gives every agent a `handoff_to_agent` tool and a list of all available agents with their descriptions. The current agent reads the descriptions, decides who should go next, and calls the tool with a message. The `description` field on each agent is load-bearing -- it is what agents read to make routing decisions.

### Context Passing: The Running Brief

Each agent starts with a blank conversation -- Strands calls `reset_executor_state()` between handoffs, so agents do **not** share chat history. The only context that survives is the **handoff message**.

To prevent ideas from being lost, every agent follows a **running brief protocol** defined in `IDEATION_RULES`:

```
── RUNNING BRIEF ──
topic_refiner: A warehouse fire at dusk — warm destruction, industrial setting.

baker: The heat of the fire mirrors the heat of an oven. Crust as char,
       bread as building. The transformation is the same.

artist: Triptych composition. Left panel: raw dough/raw concrete. Center:
        the moment of transformation — fire/oven. Right: aftermath — bread/ruin.

art_director (checkpoint): Strong concept. Push the materiality harder.
The center panel should feel like you can smell smoke. Send to scientist
for combustion physics.

scientist: Maillard reaction at 154°C parallels structural steel failure
at 538°C. Same browning chemistry, different scale.

── HANDOFF REASON ──
Art director for final review — concept is mature.
```

Each agent copies the entire running brief unchanged and appends their own contribution. The art director sees the full creative lineage when making final decisions.

### Handoff Rules

```
 WHO                    CAN HAND TO                         CANNOT HAND TO
 ───                    ──────────                          ──────────────

 topic_refiner          Any creative agent OR researcher    canvas, shipper,
                        (researcher first if prompt needs   art_director
                        real-world facts before ideation)

 Creative agents        Other creative agents, researcher,  canvas, shipper,
 (13 personas)          art_director                        topic_refiner

 researcher             Creative agent who requested help,  canvas, shipper,
                        OR best-fit creative agent if       topic_refiner
                        topic_refiner sent directly,
                        OR art_director if requested
                        during approval phase

 art_director           Creative agents, researcher,        topic_refiner
                        canvas, shipper

 canvas                 art_director ONLY                   Everyone else

 shipper                Nobody (terminal node)              --
```

### Research-First Routing

If the user prompt requires real-world facts before ideation can begin ("make art about a hot news topic this week"), the topic_refiner routes to the **researcher first**. The researcher searches the web, gathers facts, starts the running brief with findings, and then routes to the best creative agent. Any creative agent can also send to the researcher mid-ideation if they need facts they shouldn't guess at.

## Thresholds and Limits

```
 ┌────────────────────────────┬──────────┬──────────────────────────────────┐
 │ PARAMETER                  │ VALUE    │ WHY                              │
 ├────────────────────────────┼──────────┼──────────────────────────────────┤
 │ Max handoffs               │ 25       │ Caps total swarm length          │
 │ Max iterations             │ 30       │ Upper bound on event loop cycles │
 │ Execution timeout          │ 600s     │ Hard wall clock limit            │
 │ Node timeout               │ 300s     │ Per-agent time limit (shipper    │
 │                            │          │ needs ~120s for SD + other tools)│
 │ Sonnet max_tokens          │ 4096     │ Sufficient for creative ideation │
 │ Opus max_tokens            │ 8192     │ Art director's production        │
 │                            │          │ directive + handoff tool call    │
 │                            │          │ can exceed 4K tokens             │
 ├────────────────────────────┼──────────┼──────────────────────────────────┤
 │ Art director: canvas       │ 1        │ Initial draft + at most 1        │
 │ revision rounds            │          │ revision. Drafts are directional │
 │                            │          │ checks, not final output.        │
 │ Art director: ideation     │ 1        │ Send back to creative team at    │
 │ rounds back to creative    │          │ most once before forcing a       │
 │ team                       │          │ decision.                        │
 │ Media formats per run      │ 1-3      │ Art director picks best-fit      │
 │                            │          │ formats. Less is more.           │
 │ Shipper: retries per tool  │ 0        │ Each tool called once. If it     │
 │                            │          │ fails, skip and report.          │
 └────────────────────────────┴──────────┴──────────────────────────────────┘
```

## Context Flow: From Prompt to Production

This is the full chain of what context passes through the system:

```
 USER PROMPT
 "Make art about a hot news topic this week"
       │
       ▼
 TOPIC REFINER ──────────────────────────────────────────────────────
 Produces: creative brief (2-3 sentences)
 Passes via handoff message:
   ── RUNNING BRIEF ──
   topic_refiner: [creative brief]
       │
       ▼
 RESEARCHER (if needed) ─────────────────────────────────────────────
 Receives: creative brief + specific research question
 Searches web, gathers facts
 Passes via handoff message:
   ── RUNNING BRIEF ──
   topic_refiner: [creative brief]
   researcher: [factual findings — dates, quotes, data]
       │
       ▼
 CREATIVE AGENTS (3-5 typically) ────────────────────────────────────
 Each receives: full running brief from prior agents
 Each appends: their contribution (2-4 sentences of specific
               visual/conceptual ideas)
 Passes via handoff message:
   ── RUNNING BRIEF ──
   [all prior contributions, unchanged]
   [agent_name]: [new contribution]
       │
       ▼
 ART DIRECTOR (checkpoint or final review) ──────────────────────────
 Receives: full running brief with all creative contributions
 If checkpoint: appends steering notes, sends back to creative team
 If final review: synthesizes everything into PRODUCTION DIRECTIVE
       │
       ▼
 PRODUCTION DIRECTIVE ───────────────────────────────────────────────
 A structured document the art director writes and sends to shipper.
 This is where the art director applies TASTE — not a transcript of
 the creative team, but a synthesized vision. Contains:

   TITLE             — Final title for the piece
   CONCEPT           — 1-2 sentence core idea
   COMPOSITION       — Specific layout (foreground, midground, background)
   PALETTE           — Exact colors with hex codes
   TEXTURE & MATERIAL— Surface quality, real-world material references
   MOOD & LIGHT      — Emotional register, light source and direction
   STYLE REFERENCES  — Specific artists, movements, works
   MEDIA FORMATS     — 1-3 selected formats (SD image, ASCII, SVG, bitmap)
   SD PROMPT GUIDANCE— Keywords for Stable Diffusion (if selected)
   FILE_BASENAME     — snake_case name for all output files
       │
       ▼
 SHIPPER ────────────────────────────────────────────────────────────
 Receives: the production directive (and ONLY the directive)
 Does NOT see the running brief or creative team discussion.
 Executes each format once using dedicated tools.
 Does NOT reinterpret or improvise — faithful execution of the
 art director's specifications.
       │
       ▼
 OUTPUT FILES in ./output/
```

### What Gets Lost and Why

- **Creative team discussion details** do not reach the shipper. This is intentional -- the art director distills and sharpens. The shipper gets precise specs, not a brainstorming session.
- **Draft images** from canvas stay in `./drafts/`. They are directional tests, not final output. The shipper produces fresh final versions from the directive.
- **Each agent's full reasoning** (thinking traces) is not forwarded. Only the brief contribution in the running brief survives. The full reasoning is captured in the trace log for post-hoc analysis.

## Agents

| Agent | Model | Role | Tools |
|-------|-------|------|-------|
| `topic_refiner` | Sonnet 4.5 | Distills user prompt into creative brief, picks first agent | -- |
| `artist` | Sonnet 4.5 | Color, form, texture, composition | -- |
| `historian` | Sonnet 4.5 | Historical context, eras, artifacts | -- |
| `philosopher` | Sonnet 4.5 | Meaning, paradox, duality | -- |
| `scientist` | Sonnet 4.5 | Natural structures, phenomena, scale | -- |
| `storyteller` | Sonnet 4.5 | Narrative, character, scene | -- |
| `governor` | Sonnet 4.5 | Civic meaning, public discourse | -- |
| `general` | Sonnet 4.5 | Tension, hierarchy, strategy | -- |
| `educator` | Sonnet 4.5 | Legibility, layered meaning | -- |
| `farmer` | Sonnet 4.5 | Earthiness, seasons, deep time | -- |
| `doctor` | Sonnet 4.5 | Anatomy, vulnerability, empathy | -- |
| `baker` | Sonnet 4.5 | Transformation, craft, warmth | -- |
| `art_critic` | Sonnet 4.5 | Challenges and sharpens concepts | -- |
| `architect` | Sonnet 4.5 | Space, structure, proportion, place | -- |
| `researcher` | Sonnet 4.5 | Web search, fact-checking, current events | `tavily_search`, `calculator`, `current_time` |
| `canvas` | Sonnet 4.5 | Produces draft artwork for art director review | `python_repl` (sparingly), `generate_draft_image`, `generate_ascii_png`, `generate_svg_png`, `generate_bitmap`, `file_write`, `list_artwork_files` |
| `art_director` | **Opus 4.6** | Reviews, steers, approves, synthesizes production directive | `image_reader` |
| `shipper` | **Opus 4.6** | Executes production directive faithfully | `generate_image`, `generate_ascii_png`, `generate_svg_png`, `generate_bitmap`, `file_write`, `list_artwork_files` |

## Output Formats

The art director selects 1-3 formats that best serve the concept. Available media:

| Format | Tool | Best For | Output Files |
|--------|------|----------|-------------|
| `stable_diffusion_image` | `generate_image` (Bedrock SD 3.5) | Photorealistic, painterly | `{name}.png` |
| `ascii_art` | `generate_ascii_png` | Graphic, typographic, text-based | `{name}.png` + `{name}.txt` |
| `svg_art` | `generate_svg_png` | Geometric, diagrammatic, clean-line | `{name}.png` + `{name}.svg` |
| `bitmap_art` | `generate_bitmap` | Retro, iconic, simplified | `{name}.png` + `{name}.bmp` |

All output files use a descriptive `FILE_BASENAME` from the art director's directive (e.g. `temporal_echoes_ascii.png`, not `final_ascii.png`).

## File Structure

```
swarm/
├── run_art_swarm.py           # Entry point — builds swarm, runs it, prints summary
├── requirements.txt           # Python dependencies
├── .env                       # API keys, library paths (not committed)
├── agents/
│   ├── __init__.py
│   └── prompts.py             # System prompts for all 17 agents + IDEATION_RULES
├── tools/
│   ├── __init__.py
│   └── production_tools.py    # Custom @tool functions for art generation
├── drafts/                    # Canvas working directory (intermediate files)
├── output/                    # Final artwork produced by shipper
└── traces/                    # Per-run JSON execution traces (not committed)
```

## Quick Start

```bash
cd generative-ai-learning/Multi-Agent/swarm

# Install dependencies
pip install -r requirements.txt

# Run with a prompt
python run_art_swarm.py "Bread"

# Run interactively (prompts you for input)
python run_art_swarm.py
```

## Prerequisites

- Python 3.11+
- AWS credentials configured (Bedrock access to Claude Sonnet 4.5, Claude Opus 4.6, and Stable Diffusion 3.5)
- `TAVILY_API_KEY` in `.env` (for researcher web search)
- Optional: `cairo` native library + `cairosvg` Python package for SVG rendering

## Execution Summary

Each run prints a summary showing:

- **Agent path** -- the emergent handoff chain (e.g. `topic_refiner -> artist -> philosopher -> art_director -> canvas -> art_director -> shipper`)
- **Handoff count** -- how many times agents passed the baton
- **Agent contributions** -- truncated output from each agent
- **Tools invoked** -- which tools each agent called
- **Output files** -- final artwork with file sizes
- **Trace log** -- path to the JSON trace file

## Trace Logs

Each run saves a detailed JSON trace to `./traces/`. The trace includes:

- Prompt, timestamp, total elapsed time
- Full agent path and handoff count
- Per-agent: execution time, cycle counts, tool metrics (call/success/error counts, timing), traces, and truncated response

## Exercises to Try

### Change the prompt

Different prompts activate different creative agents:

```bash
python run_art_swarm.py "The weight of a decision"     # abstract → philosopher starts
python run_art_swarm.py "The Battle of Thermopylae"     # historical → historian starts
python run_art_swarm.py "A robot learning to feel"      # narrative → storyteller starts
python run_art_swarm.py "Sourdough"                     # craft → baker starts
```

### Try a research-first prompt

```bash
python run_art_swarm.py "Make art about a hot news topic this week"
```

Watch the topic_refiner route to the researcher first. The researcher searches the web for current events, then hands off to the creative team with real facts.

### Compare trace logs

Run the same prompt twice and diff the traces. The agent path will likely differ -- that is the swarm pattern in action.

### Read the running brief

Open a trace log and read each agent's response. You will see the RUNNING BRIEF grow as each agent appends their contribution. This is how context accumulates across the swarm.

## Common Issues

| Error | Fix |
|-------|-----|
| `ValidationException: The provided model identifier is invalid` | Check model IDs in `run_art_swarm.py`. Ensure Opus 4.6 and Sonnet 4.5 are enabled in your Bedrock region. |
| `TAVILY_API_KEY not set` | Add your key to `.env` |
| `no library called "cairo-2" was found` | Install cairo: `brew install cairo` (macOS). Add `DYLD_LIBRARY_PATH=/opt/homebrew/lib` to `.env`. |
| `Stable Diffusion error` | Verify SD 3.5 model access in Bedrock console. A placeholder image is generated if SD is unavailable. |
| `MaxTokensReachedException` | The art director's production directive exceeded token limit. Opus max_tokens is set to 8192 to handle this. If it persists, the running brief may be unusually long. |
| Shipper times out | Node timeout is 300s. If SD generation is slow, this can be tight for 3 formats. Reduce to 1-2 formats or increase `node_timeout` in `build_swarm()`. |
| Art director loops with canvas | Hard-limited to 1 revision round. If you see looping in older runs, pull the latest prompt changes. |
| Swarm times out (600s) | Reduce the number of media formats or increase `execution_timeout` in `build_swarm()`. |
