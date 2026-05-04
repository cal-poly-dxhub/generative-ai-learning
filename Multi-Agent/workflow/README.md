# Workflow Pattern: Insurance Claim Compliance Review

A **sequential workflow** of six specialized agents that review a commercial property insurance claim for compliance. Each agent runs in a fixed order, passing its findings to the next. The path is deterministic -- the same six steps every time.

## Contact

- Darren Kraker - dkraker@calpoly.edu
- Nick Osterbur - nosterbu@calpoly.edu

## How the Workflow Works

```
                               YOU PROVIDE
                               ───────────
                            data/sample_claim.json
                            (Margaret Chen, warehouse
                             fire, $185K claim)
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      WORKFLOW PIPELINE                                │
│                                                                      │
│  ┌──────────────────┐                                                │
│  │ 1. EXTRACT        │  Parse claim JSON, validate fields,           │
│  │    CLAIM DATA     │  insert into SQLite                           │
│  └────────┬─────────┘                                                │
│           │ claim_id, claimant, amount, cause                        │
│  ┌────────▼─────────┐                                                │
│  │ 2. POLICY         │  Query policies table: active dates,          │
│  │    COVERAGE       │  covered perils, exclusions, limits           │
│  └────────┬─────────┘                                                │
│           │ COVERED / NOT_COVERED / PARTIAL                          │
│  ┌────────▼─────────┐                                                │
│  │ 3. STATE          │  Look up CA regulations: filing deadlines,    │
│  │    REGULATION     │  required disclosures, settlement practices   │
│  └────────┬─────────┘                                                │
│           │ COMPLIANT / NON_COMPLIANT                                │
│  ┌────────▼─────────┐                                                │
│  │ 4. FRAUD          │  Check claim history, frequency analysis,     │
│  │    SCREENING      │  web search claimant, store evidence          │
│  └────────┬─────────┘                                                │
│           │ LOW / MEDIUM / HIGH risk                                 │
│  ┌────────▼─────────┐                                                │
│  │ 5. CALCULATE      │  Apply deductible, depreciation, coinsurance  │
│  │    PAYOUT         │  penalty, coverage cap → final dollar amount  │
│  └────────┬─────────┘                                                │
│           │ $XX,XXX.XX                                               │
│  ┌────────▼─────────┐                                                │
│  │ 6. COMPILE        │  Review all findings → issue verdict          │
│  │    VERDICT        │  Store in verdicts table                      │
│  └────────┴─────────┘                                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  VERDICT         │
                          │  APPROVED /      │
                          │  DENIED /        │
                          │  FLAGGED_FOR_    │
                          │  REVIEW          │     YOU GET
                          │                  │     ───────
                          │  + reasoning     │  Terminal summary
                          │  + payout amount │  SQLite verdict row
                          │  + audit trail   │  JSON trace log
                          └─────────────────┘
```

### Key Design Decisions

```
 ┌───────────────────────┐     ┌──────────────────────────────────────────┐
 │ DESIGN CHOICE         │     │ WHY                                      │
 ├───────────────────────┤     ├──────────────────────────────────────────┤
 │                       │     │                                          │
 │ Sequential pipeline   │────>│ Insurance compliance is a checklist.     │
 │ (vs. swarm/graph)     │     │ Every claim needs the same 6 steps in   │
 │                       │     │ the same order. No creative routing.     │
 │                       │     │                                          │
 │ Explicit result       │────>│ Each agent's output is passed as text    │
 │ passing (vs. shared   │     │ in the next agent's prompt. Students     │
 │ state)                │     │ can read exactly what each agent sees.   │
 │                       │     │                                          │
 │ SQLite (vs. external  │────>│ No infrastructure. File-based DB that    │
 │ database)             │     │ runs anywhere. Students can inspect it   │
 │                       │     │ with sqlite3 CLI after the run.          │
 │                       │     │                                          │
 │ Stub fallbacks for    │────>│ Demo works out of the box. Set env vars  │
 │ RAG + web search      │     │ to activate real Bedrock KB or Tavily.   │
 └───────────────────────┘     └──────────────────────────────────────────┘
```

## Data Layer

- **SQLite** database (`claims_review.db`) with five tables: `claims`, `policies`, `claim_history`, `search_evidence`, `verdicts`
- Pre-seeded with a policy and claim history via `setup_db.py`
- The claim is inserted at runtime by Agent 1

## Custom Tools

| Tool | Used By | Purpose |
|------|---------|---------|
| `parse_claim_json` | Agent 1 | Validate claim JSON fields |
| `insert_claim` | Agent 1 | INSERT into claims table |
| `query_db` | Agents 2-6 | Read-only SQL SELECT |
| `query_regulations` | Agent 3 | Bedrock KB RAG (or stub fallback) |
| `tavily_search` | Agent 4 | Web search for claimant |
| `store_evidence` | Agent 4 | INSERT into search_evidence table |
| `calculate` | Agent 5 | Safe arithmetic evaluation |
| `store_verdict` | Agent 6 | INSERT into verdicts table |

## File Structure

```
workflow/
├── run_workflow.py            # Entry point — builds agents, runs pipeline, prints summary
├── setup_db.py                # Creates SQLite schema + seeds policy and claim history
├── requirements.txt           # Python dependencies
├── .env                       # API keys (not committed)
├── claims_review.db           # SQLite database (created by setup_db.py, not committed)
├── data/
│   ├── sample_claim.json      # Default input: Margaret Chen warehouse fire ($185K)
│   └── seed_claim_history.json# Historical claims seeded into DB
├── tools/
│   ├── __init__.py            # Re-exports all tools
│   ├── db_tools.py            # query_db, insert_claim
│   ├── claim_tools.py         # parse_claim_json
│   ├── regulation_tools.py    # query_regulations (Bedrock KB + stub fallback)
│   ├── search_tools.py        # store_evidence
│   └── calc_tools.py          # calculate, store_verdict
├── regulations/
│   └── README.md              # Instructions for optional Bedrock KB setup
└── traces/                    # Per-run JSON execution traces (not committed)
```

## Quick Start

```bash
cd generative-ai-learning/Multi-Agent/workflow

# Install dependencies
pip install -r requirements.txt

# Create and seed the database
python setup_db.py

# Run the 6-agent pipeline
python run_workflow.py

# Or with a custom claim file
python run_workflow.py --claim data/my_claim.json
```

## Prerequisites

- Python 3.11+
- AWS credentials configured (for Bedrock model access)
- No external database needed -- SQLite is file-based

## Execution Summary

Each run prints a summary showing:

- **Steps completed** -- 6/6 with timing bars
- **Tools invoked** -- which tools each agent called
- **Final verdict** -- APPROVED / DENIED / FLAGGED_FOR_REVIEW with reasoning
- **Trace log** -- path to the JSON trace file

## Trace Logs

Each run saves a detailed JSON trace to `./traces/`. The trace includes:

- Claim ID, claim data, timestamp, total elapsed time
- Per-step: name, description, execution time, tools called, cycle counts, tool metrics, and truncated response

## Sample Claim

The default demo processes claim `CLM-2024-00847`:

| Field | Value |
|-------|-------|
| Claimant | Margaret Chen |
| Property | 4521 Industrial Blvd, Los Angeles, CA 90058 |
| Type | Warehouse |
| Cause | Fire (electrical panel) |
| Amount | $185,000.00 |
| Loss Date | 2024-09-15 |
| Filed Date | 2024-10-02 |

## Optional Enhancements

- **Real RAG**: Set `KNOWLEDGE_BASE_ID` env var to use Bedrock Knowledge Bases for regulation lookup. See `regulations/README.md`.
- **Real web search**: The pipeline uses Tavily for web search. Set `TAVILY_API_KEY` in `.env`.

## Common Issues

| Error | Fix |
|-------|-----|
| `Database not found` | Run `python setup_db.py` first |
| `The SSO session associated with this profile has expired` | Run `aws sso login` again |
| `ValidationException: model identifier is invalid` | Check model ID in `run_workflow.py` |
| `TAVILY_API_KEY not set` | Add your Tavily key to `.env`, or the fraud screening step will skip web search |
| `UNIQUE constraint failed` on re-run | The claim already exists. Run `python setup_db.py` to reset the database. |
