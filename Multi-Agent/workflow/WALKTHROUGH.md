# Insurance Claim Compliance Review: Step-by-Step Walkthrough

## What You Will Build

A pipeline where six AI agents each handle one step of an insurance claim review -- from parsing the claim, to checking policy coverage, to screening for fraud, to calculating the payout and issuing a verdict. By the end, you will understand how the **workflow pattern** works: agents run in a fixed sequence, each passing its findings to the next.

```
 Claim JSON ──> 6 agents in sequence ──> APPROVED / DENIED / FLAGGED_FOR_REVIEW
```

---

## Step 1: Navigate to the Workflow Directory

```bash
cd generative-ai-learning/Multi-Agent/workflow
```

You should see:

```
run_workflow.py         # Main pipeline script
setup_db.py             # Creates and seeds the database
data/
  sample_claim.json     # The claim we will process
  seed_claim_history.json
tools/
  db_tools.py           # query_db, insert_claim
  claim_tools.py        # parse_claim_json
  regulation_tools.py   # query_regulations
  search_tools.py       # store_evidence
  calc_tools.py         # calculate, store_verdict
```

Verify:

```bash
ls run_workflow.py setup_db.py data/sample_claim.json tools/
```

---

## Step 2: Make Sure You Are Signed In to AWS

```bash
aws sso login --profile default
```

Replace `default` with your profile name. Approve the sign-in in your browser.

### Verify your identity

```bash
aws sts get-caller-identity --profile default
```

---

## Step 3: Install Dependencies

If you are using the course virtual environment:

```bash
source ../../venv/bin/activate
pip install -r requirements.txt
```

This installs `strands-agents[bedrock]`, `strands-agents-tools`, and `boto3`.

---

## Step 4: Review the Sample Claim

Open `data/sample_claim.json`:

```json
{
  "claim_id": "CLM-2024-00847",
  "policy_id": "POL-CA-20221015",
  "claimant_name": "Margaret Chen",
  "loss_date": "2024-09-15",
  "filed_date": "2024-10-02",
  "claim_amount": 185000.00,
  "property_address": "4521 Industrial Blvd, Los Angeles, CA 90058",
  "property_type": "warehouse",
  "cause_of_loss": "fire",
  "description": "Fire originating in electrical panel caused significant damage...",
  "state": "CA"
}
```

This is what Agent 1 will parse. Notice the structured fields -- claim ID, policy ID, dollar amount, dates, cause of loss. Each subsequent agent will query different aspects of this claim.

---

## Step 5: Create and Seed the Database

```bash
python setup_db.py
```

You should see output confirming the tables were created and seed data was inserted. This creates `claims_review.db` with:

| Table | Purpose | Seeded? |
|-------|---------|---------|
| `claims` | Incoming claims | No -- Agent 1 inserts at runtime |
| `policies` | Policy terms (coverage, limits, deductible) | Yes -- one policy matching our claim |
| `claim_history` | Prior claims on this policy | Yes -- 3-4 historical claims |
| `search_evidence` | Web search results for audit trail | No -- Agent 4 inserts at runtime |
| `verdicts` | Final decisions | No -- Agent 6 inserts at runtime |

### Inspect the database

```bash
sqlite3 claims_review.db ".tables"
sqlite3 claims_review.db "SELECT * FROM policies"
sqlite3 claims_review.db "SELECT * FROM claim_history"
```

Notice the policy has a $500K coverage limit, $10K deductible, and 80% coinsurance requirement. Agent 5 will use these numbers to calculate the payout.

---

## Step 6: Run the Pipeline

```bash
python run_workflow.py
```

Watch the terminal. Each step prints its agent name, tool calls, and reasoning:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WORKFLOW PATTERN DEMO — Insurance Claim Compliance Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ▶ Step 1/6: Extract Claim Data
      ↳ Tool #1: parse_claim_json
      ↳ Tool #2: insert_claim
  ✓ Step 1: Extract Claim Data done (8.2s)

  ▶ Step 2/6: Policy Coverage Check
      ↳ Tool #1: query_db
      ↳ Tool #2: query_db
  ✓ Step 2: Policy Coverage Check done (12.1s)

  ...

  ▶ Step 6/6: Compile Verdict
      ↳ Tool #1: query_db
      ↳ Tool #2: store_verdict
  ✓ Step 6: Compile Verdict done (9.4s)
```

### What each step does

**Step 1 -- Extract Claim Data**: Parses the JSON, validates required fields, inserts a row into the `claims` table.

**Step 2 -- Policy Coverage Check**: Queries the `policies` table. Checks: Is the policy active on the loss date? Is fire a covered peril? Is $185K within the $500K limit?

**Step 3 -- State Regulation Check**: Looks up California insurance regulations. Checks filing deadlines (was the claim filed within the required timeframe?) and settlement practices.

**Step 4 -- Fraud Screening**: Queries `claim_history` for prior claims. Checks frequency, escalating amounts, suspicious timing. Searches the web for the claimant. Stores evidence in the database.

**Step 5 -- Calculate Payout**: The math step. Pulls policy terms (deductible, depreciation rate, coinsurance percentage) and calculates the adjusted payout step by step. Uses the `calculate` tool for each arithmetic operation.

**Step 6 -- Compile Verdict**: Reviews all prior findings and issues APPROVED, DENIED, or FLAGGED_FOR_REVIEW. Stores the verdict in the `verdicts` table.

---

## Step 7: Inspect the Results

### Execution summary

The pipeline prints a summary with timing bars and the final verdict. Read through it to see which steps took longest.

### Database verdict

```bash
sqlite3 claims_review.db "SELECT verdict, approved_amount, reasoning FROM verdicts WHERE claim_id='CLM-2024-00847'"
```

### Search evidence

```bash
sqlite3 claims_review.db "SELECT search_query, result_summary FROM search_evidence WHERE claim_id='CLM-2024-00847'"
```

### Trace log

```bash
ls traces/
cat traces/$(ls -t traces/ | head -1) | python -m json.tool | head -60
```

The trace captures per-step timing, tool calls, cycle counts, and truncated responses.

---

## Step 8: Understand the Agent Chaining

Open `run_workflow.py` and find the `prompts` list (around line 261). This is how context flows between agents:

```python
prompts = [
    f"Parse and store this insurance claim. Here is the claim JSON:\n{claim_json_str}",

    f"Check policy coverage for claim {claim_id}...",

    f"Check state regulations for claim {claim_id}... "
    f"Previous step (coverage check) found: {prev}",

    f"Screen claim {claim_id} for fraud... "
    f"Policy coverage result: {coverage}",

    f"Calculate the payout for claim {claim_id}. "
    f"Coverage status: {coverage}. Fraud assessment: {fraud}",

    f"Compile the final verdict for claim {claim_id}. "
    f"Coverage: {coverage}\nRegulations: {regulation}\n"
    f"Fraud screening: {fraud}\nPayout calculation: {payout}",
]
```

Each agent gets the raw results from relevant prior steps injected into its prompt. Agent 6 (verdict) receives findings from all four prior analysis steps.

This is the key difference from the swarm pattern: **you control exactly what each agent sees**. There is no emergent routing -- the pipeline is hardcoded in Python.

---

## Step 9: Understand the Tools

Open `tools/db_tools.py`. The `query_db` tool is the most widely used:

```python
@tool
def query_db(sql: str) -> str:
    """Execute a read-only SQL query against the claims database."""
```

Notice it only allows SELECT statements -- agents cannot modify data through this tool. Writes go through purpose-built tools (`insert_claim`, `store_evidence`, `store_verdict`) that validate their inputs.

Open `tools/calc_tools.py`. The `calculate` tool uses restricted evaluation:

```python
@tool
def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression."""
```

It only allows numbers and arithmetic operators -- no arbitrary code execution. This is a security boundary: the agent can do math but cannot run arbitrary Python.

---

## Step 10: Read the System Prompts

Back in `run_workflow.py`, find the `AGENTS` list (around line 148). Each agent has a `system_prompt` that defines its role and step-by-step instructions.

Compare Agent 2 (Policy Coverage) and Agent 4 (Fraud Screening):

- Agent 2 is given a precise checklist: active dates, covered perils, exclusions, limits.
- Agent 4 is given a more investigative mandate: analyze patterns, search the web, flag concerns.

Both are the same Claude model. The difference in behavior comes entirely from the system prompt and the tools available.

---

## Step 11: Re-run and Compare

Reset the database and run again:

```bash
python setup_db.py
python run_workflow.py
```

Because the workflow is deterministic (same 6 steps, same order), the overall structure will be identical. But the LLM responses may vary slightly -- different phrasing, different emphasis in the fraud analysis, possibly a slightly different payout calculation if the agent sequences its arithmetic differently.

Compare the two trace logs to see where the runs diverged.

---

## Step 12: Write Your Own Claim

Create `data/my_claim.json`:

```json
{
  "claim_id": "CLM-2024-99999",
  "policy_id": "POL-CA-20221015",
  "claimant_name": "Margaret Chen",
  "loss_date": "2024-12-01",
  "filed_date": "2024-12-15",
  "claim_amount": 450000.00,
  "property_address": "4521 Industrial Blvd, Los Angeles, CA 90058",
  "property_type": "warehouse",
  "cause_of_loss": "fire",
  "description": "Second major fire in three months. Complete loss of inventory and structural damage.",
  "state": "CA"
}
```

This claim has red flags: $450K amount (close to the $500K limit), second fire in three months, same claimant. Run it:

```bash
python setup_db.py
python run_workflow.py --claim data/my_claim.json
```

Watch Agent 4 (Fraud Screening) -- it should flag the claim history pattern. Watch Agent 6 (Verdict) -- it may issue FLAGGED_FOR_REVIEW instead of APPROVED.

---

## How It Compares to the Swarm Pattern

```
 WORKFLOW                                 SWARM
 ────────                                 ─────

 ┌─────────┐                              ┌─────────┐
 │ Agent 1  │───> Agent 2 ───> Agent 3     │ Agent A  │──?──> Agent C ──?──> ...
 │          │                              │          │──?──> Agent B
 └─────────┘                              └─────────┘

 Path hardcoded in Python                 Path decided at runtime by LLMs
 Deterministic                            Non-deterministic
 Good for compliance/sequential tasks     Good for creative/exploratory tasks
 Easy to debug and audit                  Harder to debug
 Each agent receives prior output         Agents carry a running brief
```

The workflow pattern is the right choice when:
- Every case needs the same steps in the same order
- Auditability matters (insurance, compliance, legal)
- You need to control exactly what each agent sees
- The output must be reproducible

---

## Quick Reference

| Task | Command |
|------|---------|
| Create database | `python setup_db.py` |
| Run pipeline | `python run_workflow.py` |
| Run custom claim | `python run_workflow.py --claim data/my_claim.json` |
| View verdict | `sqlite3 claims_review.db "SELECT * FROM verdicts"` |
| View evidence | `sqlite3 claims_review.db "SELECT * FROM search_evidence"` |
| View latest trace | `cat traces/$(ls -t traces/ \| head -1) \| python -m json.tool` |
| Reset database | `python setup_db.py` |

## Troubleshooting

| Error | Solution |
|-------|----------|
| `Database not found. Run setup_db.py first` | Run `python setup_db.py` |
| `The SSO session associated with this profile has expired` | Run `aws sso login` again |
| `UNIQUE constraint failed: claims.claim_id` | Claim already exists. Run `python setup_db.py` to reset. |
| `TAVILY_API_KEY not set` | Add key to `.env`. Fraud screening will skip web search without it. |
| `ValidationException: model identifier is invalid` | Check model ID in `run_workflow.py`. Ensure Sonnet 4.5 is enabled in Bedrock. |
| Agent gives wrong payout math | The `calculate` tool is deterministic. Check the agent's reasoning in the trace -- it may have sequenced the operations differently. |
