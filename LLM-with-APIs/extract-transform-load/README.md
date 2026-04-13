# ETL Pipeline: PDF Document Extraction with AWS Bedrock

Extract structured data from PDFs using an LLM. Run the script, see the output in terminal, check the JSON file.

## Contact

- Darren Kraker - dkraker@calpoly.edu
- Nick Osterbur - nosterbu@calpoly.edu

## How the Pipeline Works

This project follows an **ETL (Extract, Transform, Load)** pattern — a common way to move data from one format to another using AI in the middle.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ETL PIPELINE OVERVIEW                            │
└─────────────────────────────────────────────────────────────────────────┘

  YOU PROVIDE                 AI DOES THE WORK                YOU GET
  ───────────                 ────────────────                ────────

  ┌──────────┐    ┌──────────────────────────────┐    ┌──────────────┐
  │          │    │                              │    │              │
  │   PDF    │───>│   1. EXTRACT   2. TRANSFORM  │───>│     JSON     │
  │ Document │    │                              │    │   Database   │
  │          │    │   Pull text    Send text to   │    │              │
  └──────────┘    │   from PDF     AI with your   │    └──────────────┘
                  │               prompt          │
  ┌──────────┐    │                              │
  │  Prompt  │───>│          3. LOAD             │
  │ Template │    │          Save AI response    │
  │ (.txt)   │    │          as structured JSON  │
  └──────────┘    └──────────────────────────────┘
```

### Step-by-Step Breakdown

```
 STEP 1: EXTRACT                STEP 2: TRANSFORM               STEP 3: LOAD
 ══════════════                 ═════════════════                ════════════

 ┌────────────┐                ┌─────────────────┐             ┌─────────────┐
 │ PDF File   │                │ Prompt Template  │             │ output.json │
 │            │                │ (passed via CLI) │             │             │
 │ "Meeting   │  pdfplumber    │ ┌─────────────┐  │  Bedrock    │ [           │
 │  held on   │ ──────────>    │ │ "Extract    │  │ ────────>   │  {          │
 │  Jan 5..." │  raw text      │ │  the date,  │  │  valid JSON │   "date":   │
 │            │                │ │  location.. │  │             │   "Jan 5",  │
 └────────────┘                │ │             │  │             │   ...       │
                               │ │ {{PAYLOAD}} │  │             │  }          │
       Raw text gets           │ │  ↑          │  │             │ ]           │
       injected here ─────────>│ │  │ injected  │  │             └─────────────┘
                               │ │  └──────────│  │                   │
                               │ └─────────────┘  │              Append each
                               └─────────────────┘              run to build
                                       │                        a database
                                       ▼                        over time
                               ┌─────────────────┐
                               │  AWS Bedrock     │
                               │  ┌─────────────┐ │
                               │  │ Claude LLM  │ │
                               │  │             │ │
                               │  │ model_id    │ │
                               │  │ temperature │ │
                               │  └─────────────┘ │
                               └─────────────────┘
                               Config controls these
                               settings (config.json)
```

### Running the Pipeline

```
python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/extract_meeting.txt

  ┌──────────────┐   ┌───────────────────┐
  │ --pdf        │   │ --prompt          │
  │ Which PDF    │   │ Which prompt      │
  │ to process   │   │ template to use   │
  └──────┬───────┘   └────────┬──────────┘
         │                    │
         └────────┬───────────┘
                  ▼
         ┌────────────────┐        ┌──────────────┐
         │    etl.py      │───────>│  Terminal     │
         │  reads config, │        │  shows each  │
         │  runs pipeline │        │  step live   │
         └────────┬───────┘        └──────────────┘
                  │
                  ▼
         ┌────────────────┐
         │  output.json   │
         │  (inspect this │
         │   after run)   │
         └────────────────┘
```

### What You Can Change (and What Happens)

```
 ┌───────────────────┐     ┌──────────────────────────────────────────┐
 │ CHANGE THIS...    │     │ ...TO SEE THIS                          │
 ├───────────────────┤     ├──────────────────────────────────────────┤
 │                   │     │                                          │
 │ Prompt template   │────>│ Different fields extracted, different    │
 │ (swap .txt file   │     │ structure, more/less detail              │
 │  via --prompt)    │     │                                          │
 │                   │     │                                          │
 │ Temperature       │────>│ Lower = consistent, factual output      │
 │ (config.json)     │     │ Higher = creative, varied output         │
 │                   │     │                                          │
 │ Model ID          │────>│ Different models = different quality,    │
 │ (config.json)     │     │ speed, cost tradeoffs                    │
 │                   │     │                                          │
 │ Input PDF         │────>│ Same pipeline processes any document     │
 │ (swap via --pdf)  │     │ — that's the power of ETL               │
 └───────────────────┘     └──────────────────────────────────────────┘
```

### The Big Picture: Why This Matters

```
 BEFORE (Manual)                          AFTER (This Pipeline)

 ┌──────┐  ┌──────┐  ┌──────┐            ┌──────┐  ┌──────┐  ┌──────┐
 │ PDF  │  │ PDF  │  │ PDF  │            │ PDF  │  │ PDF  │  │ PDF  │
 │  1   │  │  2   │  │  3   │            │  1   │  │  2   │  │  3   │
 └──┬───┘  └──┬───┘  └──┬───┘            └──┬───┘  └──┬───┘  └──┬───┘
    │         │         │                    │         │         │
    ▼         ▼         ▼                    └────┬────┘─────────┘
 ┌──────┐  ┌──────┐  ┌──────┐                    ▼
 │Person│  │Person│  │Person│            ┌────────────────┐
 │reads │  │reads │  │reads │            │  Run pipeline  │
 │& types│ │& types│ │& types│           │  once per PDF  │
 └──┬───┘  └──┬───┘  └──┬───┘            └───────┬────────┘
    │         │         │                         │
    ▼         ▼         ▼                         ▼
 Hours of work, errors,              ┌────────────────────┐
 inconsistent formats                │  Consistent JSON   │
                                     │  database grows    │
                                     │  automatically     │
                                     └────────────────────┘
                                     Seconds per document,
                                     structured & searchable
```

## File Structure

```
extract-transform-load/
├── config.json                    # Model ID, temperature, max tokens, region
├── prompts/
│   ├── extract_meeting.txt        # Prompt for meeting agendas
│   └── extract_invoice.txt        # Prompt for invoices
├── data/
│   ├── Board-of-Supervisors-Agenda.pdf
│   └── output.json                # Running JSON database (created on first run)
├── etl.py                         # The pipeline script
└── README.md
```

## Quick Start

All commands assume you have navigated into this directory first:

```bash
cd generative-ai-learning/LLM-with-APIs/extract-transform-load
```

### 1. Install dependencies

```bash
pip install boto3 pdfplumber
```

### 2. Extract a meeting agenda

```bash
python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/extract_meeting.txt
```

### 3. Extract an invoice

```bash
python etl.py --pdf data/invoice-sample.pdf --prompt prompts/extract_invoice.txt
```

### 4. Check the output

Open `data/output.json` — each run appends a new record to the array. Two runs = two records, each with different structure based on the prompt used.

## Exercises to Try

### Change the temperature
Edit `config.json` — set `"temperature": 1.0`, re-run an extraction, and compare the output to the `0.0` run.

### Change the model
Edit `config.json` — swap the `model_id`, re-run, and compare quality/speed.

### Write your own prompt
Create a new `.txt` file in `prompts/`. Use `{{PAYLOAD}}` where the PDF text should go. Run it:
```bash
python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/my_prompt.txt
```

## Config Reference

`config.json`:

| Field | Description | Example |
|-------|-------------|---------|
| `model_id` | Bedrock model identifier | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| `temperature` | Randomness (0.0 = deterministic, 1.0 = creative) | `0.0` |
| `max_tokens` | Max response length | `4096` |
| `region` | AWS region | `us-west-2` |
| `profile_name` | AWS CLI profile name | `GSB570-BedrockOnly-490332585640` |

## CLI Reference

```
python etl.py --pdf <path> --prompt <path> [--output <path>] [--config <path>]

  --pdf       Path to input PDF file
  --prompt    Path to prompt template (.txt with {{PAYLOAD}} placeholder)
  --output    Path to output JSON file (default: output.json)
  --config    Path to config file (default: config.json)
```

## Common Issues

| Error | Fix |
|-------|-----|
| `No module named 'pdfplumber'` | `pip install pdfplumber` |
| `No credentials found` | Check AWS CLI config and profile name in `config.json` |
| `Access denied to model` | Verify Bedrock model access in AWS console |
| `JSON decode error` | Simplify your prompt or check the raw output printed to terminal |
