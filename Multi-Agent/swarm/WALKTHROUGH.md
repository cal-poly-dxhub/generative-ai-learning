# Collaborative Art Generator: Step-by-Step Walkthrough

## What You Will Build

A system where 17 AI agents with different creative perspectives collaborate to produce artwork from a single text prompt. By the end, you will understand how the **swarm pattern** works -- agents self-organize, hand off to each other, and converge on a final output without a hardcoded pipeline.

```
 "Bread" ──> 17 agents debate ──> art director synthesizes ──> shipper produces artwork
```

---

## Step 1: Navigate to the Swarm Directory

```bash
cd generative-ai-learning/Multi-Agent/swarm
```

You should see:

```
run_art_swarm.py       # Main script
requirements.txt       # Dependencies
agents/
  prompts.py           # All 17 agent system prompts
tools/
  production_tools.py  # Custom art generation tools
drafts/                # Working directory for canvas agent
output/                # Final artwork lands here
```

Verify:

```bash
ls run_art_swarm.py agents/prompts.py tools/production_tools.py
```

---

## Step 2: Make Sure You Are Signed In to AWS

```bash
aws sso login --profile default
```

Replace `default` with your profile name. A browser window will open -- approve the sign-in.

### Verify your identity

```bash
aws sts get-caller-identity --profile default
```

You need Bedrock access to three models:
- Claude Sonnet 4.5 (creative team)
- Claude Opus 4.6 (art director + shipper)
- Stable Diffusion 3.5 (image generation)

---

## Step 3: Install Dependencies

If you are using the course virtual environment:

```bash
source ../../venv/bin/activate
pip install -r requirements.txt
```

This installs `strands-agents[bedrock]`, `strands-agents-tools`, Pillow, matplotlib, numpy, and pyfiglet.

### Optional: SVG rendering

For high-quality SVG-to-PNG conversion:

```bash
brew install cairo          # macOS
pip install cairosvg
```

Then add to `.env`:

```
DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

The swarm works without this -- SVG output will use a text-based fallback.

---

## Step 4: Set Up Environment Variables

Create a `.env` file (or edit the existing one):

```
TAVILY_API_KEY=your-key-here
```

The researcher agent uses Tavily for web search. If you don't have a key, the researcher will still function but web searches will fail gracefully.

---

## Step 5: Run the Swarm

```bash
python run_art_swarm.py "Bread"
```

Watch the terminal. You will see agents activate one by one:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SWARM PATTERN DEMO — Collaborative Art Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Prompt: Bread

      Thinking: The user wants art about bread...
      ↳ Handoff: topic_refiner → baker

      Thinking: Bread as transformation, the alchemy of crust...
      ↳ Handoff: baker → artist

      Thinking: A still life, but not static...
      ↳ Handoff: artist → art_director

      ↳ Handoff: art_director → canvas
      ↳ Tool: generate_draft_image

      ↳ Handoff: canvas → art_director
      ↳ Tool: image_reader

      ↳ Handoff: art_director → shipper
      ↳ Tool: generate_image
      ↳ Tool: generate_ascii_png
      ↳ Tool: generate_svg_png
```

### What just happened

1. **topic_refiner** read your prompt and wrote a creative brief. It decided bread is about craft and transformation, so it handed off to the **baker**.
2. **baker** contributed ideas about kneading, rising, the golden spectrum of crust. It handed off to the **artist** for visual specificity.
3. **artist** described composition, palette, materials. It handed off to the **art_director** for review.
4. **art_director** (Opus 4.6) evaluated the accumulated ideas. It commissioned a draft from **canvas**, inspected the image, then wrote a PRODUCTION DIRECTIVE and handed to **shipper**.
5. **shipper** (Opus 4.6) executed the directive, producing final artwork in multiple formats.

Your output files are in `./output/`.

---

## Step 6: Inspect the Output

List what was produced:

```bash
ls -la output/
```

Open the PNG files in your image viewer or Finder. You will see artwork in different media -- an AI-generated image, ASCII art, vector art, pixel art -- all derived from the same creative concept.

---

## Step 7: Read the Trace Log

Each run saves a JSON trace to `./traces/`:

```bash
ls traces/
cat traces/$(ls -t traces/ | head -1) | python -m json.tool | head -40
```

The trace shows:
- Which agents ran and in what order
- How long each agent took
- Which tools each agent called
- Truncated responses showing the running brief

### Follow the running brief

Search for "RUNNING BRIEF" in the trace to see how ideas accumulated. Each agent copies the entire brief from the previous handoff and appends their own contribution. This is how context survives across agents that don't share conversation history.

---

## Step 8: Run It Again with the Same Prompt

```bash
python run_art_swarm.py "Bread"
```

Compare the execution summary to your first run. The agent path will likely be different -- maybe the **farmer** gets involved this time, or the **philosopher** adds a reflection on sustenance. This is the swarm pattern: the path is emergent, not deterministic.

Compare the two trace logs side by side to see how the same prompt produced different creative journeys.

---

## Step 9: Try Different Prompts

Different prompts activate different parts of the swarm:

```bash
# Abstract concept → philosopher likely starts
python run_art_swarm.py "The weight of a decision"

# Historical subject → historian likely starts
python run_art_swarm.py "The fall of Rome"

# Nature/science → scientist likely starts
python run_art_swarm.py "Bioluminescence in the deep ocean"

# Narrative → storyteller likely starts
python run_art_swarm.py "A letter that was never sent"
```

Watch which agent the topic_refiner chooses first. The routing is guided by the system prompt but decided by the LLM.

---

## Step 10: Read the Prompts

Open `agents/prompts.py` in your editor. This is the most important file in the swarm -- it defines every agent's personality and behavior.

### Things to notice

**IDEATION_RULES** (line 5): Every creative agent gets these rules appended to their system prompt. They define the running brief format, handoff rules, and when to go to the art director.

**TOPIC_REFINER_PROMPT** (line 42): Contains explicit routing hints -- "Visual/aesthetic topics -> hand off to artist" -- but the LLM makes the final call.

**ART_DIRECTOR_PROMPT** (line 249): The longest prompt. Two modes:
- MODE 1 (CHECKPOINT): Mid-ideation feedback. Steers the creative team.
- MODE 2 (FINAL REVIEW): Synthesizes a PRODUCTION DIRECTIVE with locked-down specs.

**SHIPPER_PROMPT** (line 372): Told explicitly NOT to reinterpret. Executes the directive faithfully.

### The handoff mechanism

There is no routing code. Strands gives every agent a `handoff_to_agent` tool and a list of available agents with descriptions. The LLM reads the descriptions and calls the tool:

```
handoff_to_agent(agent_name="philosopher", message="── RUNNING BRIEF ──\n...")
```

The `description` field on each agent is load-bearing -- it is what the current agent reads to decide who comes next.

---

## Step 11: Understand the Two-Tier Model Architecture

Open `run_art_swarm.py` and look at `build_swarm()` (line 155):

```python
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    max_tokens=4096,
)
opus_model = BedrockModel(
    model_id="us.anthropic.claude-opus-4-6-v1",
    max_tokens=4096,
)
```

- **Sonnet 4.5**: 15 agents (topic_refiner, all 13 creative personas, researcher, canvas). Fast, cheap, good for brainstorming.
- **Opus 4.6**: 2 agents (art_director, shipper). The most capable model handles final creative decisions and production execution.

This is a common pattern in multi-agent systems: use smaller models for volume work and reserve the most capable model for high-stakes decisions.

---

## Step 12: Understand the Custom Tools

Open `tools/production_tools.py`. Each tool is a Python function decorated with `@tool` from Strands:

```python
@tool
def generate_ascii_png(
    description: str,
    width: int = 80,
    style: str = "block",
    output_dir: str = "",
    filename: str = "",
) -> str:
```

The `@tool` decorator exposes the function to the agent as a callable tool. The docstring becomes the tool description the LLM reads. The type hints define the tool's input schema.

### Draft vs. final

- **Canvas** uses tools that default to `./drafts/` -- intermediate work.
- **Shipper** uses tools with `output_dir="./output/"` -- final deliverables.
- Both pass a `filename` derived from the art director's `FILE_BASENAME` directive.

---

## How It Compares to the Workflow Pattern

```
 SWARM                                    WORKFLOW
 ─────                                    ────────

 ┌─────────┐                              ┌─────────┐
 │ Agent A  │──?──> Agent C ──?──> ...     │ Agent 1  │───> Agent 2 ───> Agent 3
 │          │──?──> Agent B               │          │
 └─────────┘                              └─────────┘

 Path decided at runtime by LLMs          Path hardcoded in Python
 Non-deterministic                        Deterministic
 Good for creative/exploratory tasks      Good for compliance/sequential tasks
 Harder to debug                          Easy to debug
 Each agent has its own conversation      Each agent receives prior agent output
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Run with prompt | `python run_art_swarm.py "Your prompt"` |
| Run interactively | `python run_art_swarm.py` |
| View output | `ls output/` |
| View latest trace | `cat traces/$(ls -t traces/ \| head -1) \| python -m json.tool` |
| Clean output | `rm output/*` (keep .gitkeep) |
| Clean drafts | `rm drafts/*` (keep .gitkeep) |

## Troubleshooting

| Error | Solution |
|-------|----------|
| `The SSO session associated with this profile has expired` | Run `aws sso login` again |
| `ValidationException: The provided model identifier is invalid` | Check that Opus 4.6 and Sonnet 4.5 are enabled in your Bedrock console |
| `TAVILY_API_KEY not set` | Add your Tavily key to `.env` |
| `no library called "cairo-2" was found` | Install cairo (`brew install cairo`) and set `DYLD_LIBRARY_PATH=/opt/homebrew/lib` in `.env` |
| `Stable Diffusion error` / placeholder image | Enable SD 3.5 Large in Bedrock console. A placeholder PNG is generated if SD is unavailable. |
| Swarm loops or times out | The max is 25 handoffs / 600s. If agents keep cycling, try a more specific prompt. |
| Generic filenames in output | This was fixed -- art director now passes FILE_BASENAME. If you see `final_svg.png`, run again with latest code. |
