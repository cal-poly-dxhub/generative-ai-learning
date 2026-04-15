# ETL with LLMs: Step-by-Step Walkthrough

## What You Will Build

A pipeline that reads a PDF, sends the text to an LLM with a prompt you control, and saves structured JSON output to a running database file. By the end, you will understand how to use an LLM as a data extraction tool — and how changing the prompt, temperature, or model changes the output.

```
 PDF Document ──> Extract Text ──> Inject into Prompt ──> Call LLM ──> Structured JSON
```

---

## Step 1: Clone the Repository

If you haven't already, open a terminal and run:

```bash
git clone https://github.com/cal-poly-dxhub/generative-ai-learning.git
```

Once the clone finishes, navigate into the ETL directory:

```bash
cd generative-ai-learning/LLM-with-APIs/extract-transform-load
```

You should see the following files:

```
etl.py                         # The pipeline script
config.json                    # Model settings (model ID, temperature, etc.)
prompts/
  extract_meeting.txt          # Prompt template for meeting agendas
  extract_invoice.txt          # Prompt template for invoices
data/
  Board-of-Supervisors-Agenda.pdf
  invoice-sample.pdf
```

Verify:

```bash
ls etl.py config.json prompts/ data/
```

---

## Step 2: Make Sure You Are Signed In to AWS with SSO

AWS Single Sign-On (SSO) lets you authenticate with your organization's credentials instead of managing long-lived access keys.

Each time you start a new work session, sign in with:

```bash
aws sso login --profile default
```

Replace `default` with your profile name if you chose a different one during setup.

A browser window will open. Approve the sign-in request, then return to your terminal.

### Verify your identity

```bash
aws sts get-caller-identity --profile default
```

You should see output like:

```json
{
    "UserId": "AROA...:your-email@example.com",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/YourRole/your-email@example.com"
}
```

If you see an error about expired credentials, run `aws sso login --profile default` again.

---

## Step 3: Install Python Dependencies

You need two packages: `boto3` (AWS SDK) and `pdfplumber` (PDF text extraction).

If you are using a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows
pip install boto3 pdfplumber
```

If not using a venv:

```bash
pip install boto3 pdfplumber
```

---

## Step 4: Review the Config File

Open `config.json` in your editor:

```json
{
  "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
  "temperature": 0.0,
  "max_tokens": 4096,
  "region": "us-west-2",
  "profile_name": "457651165565_AdministratorAccess"
}
```

| Field | What It Controls |
|-------|-----------------|
| `model_id` | Which LLM to call. You can swap this to try different models. |
| `temperature` | Randomness of output. 0.0 = deterministic, 1.0 = creative. |
| `max_tokens` | Maximum length of the LLM response. |
| `region` | AWS region where Bedrock is available. |
| `profile_name` | Your AWS CLI profile name. Update this to match yours. |

**Important:** Make sure `profile_name` matches the profile you used in Step 2. If your profile is called `default`, change it to `"default"`.

---

## Step 5: Review a Prompt Template

Open `prompts/extract_meeting.txt` in your editor. Notice the structure:

1. **Role** — The first line tells the LLM who it is: an expert government document analyst.
2. **`<document>`** — The PDF text gets injected here via `{{PAYLOAD}}`. This is placed near the top because large, important context should come first.
3. **`<rules>`** — Explicit constraints wrapped in XML-style tags. The model follows these more reliably when they are clearly encapsulated.
4. **`<instructions>`** — Chain-of-thought (CoT) reasoning. Instead of asking for the answer directly, we tell the model to think step by step.
5. **`<output_schema>`** — The exact JSON structure we expect back.
6. **`<example>`** — A concrete input/output pair so the model knows exactly what "good" looks like.

These are **API-level prompt engineering techniques**. You are not chatting with the model — you are programming its behavior through the prompt.

---

## Step 6: Run the Pipeline — Meeting Agenda

Now run the ETL script on the Board of Supervisors agenda:

```bash
python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/extract_meeting.txt
```

Watch the terminal output. You will see each step of the pipeline:

```
============================================================
  ETL PIPELINE: PDF -> Prompt + LLM -> JSON
============================================================

[EXTRACT] Reading PDF: data/Board-of-Supervisors-Agenda.pdf
[EXTRACT] Got 18093 characters from 7 pages

[TRANSFORM] Using prompt template: prompts/extract_meeting.txt
[TRANSFORM] Model: us.anthropic.claude-sonnet-4-20250514-v1:0  |  Temperature: 0.0
[TRANSFORM] Calling Bedrock API...
[TRANSFORM] Valid JSON received

[PREVIEW] LLM output:
{
  "meeting_title": "Board of Supervisors Agenda",
  "date": "Tuesday, April 4, 2023",
  ...
}

[LOAD] Appended record #1 to data/output.json

============================================================
  DONE. Check output file: data/output.json
============================================================
```

### What just happened

1. **Extract** — `pdfplumber` pulled raw text from all 7 pages of the PDF.
2. **Transform** — The script loaded `prompts/extract_meeting.txt`, replaced `{{PAYLOAD}}` with the raw text, and sent the assembled prompt to Claude via the Bedrock API.
3. **Load** — The LLM returned structured JSON. The script parsed it and appended it to `data/output.json`.

Open `data/output.json` in your editor to inspect the result.

---

## Step 7: Run the Pipeline — Invoice

Now run the same pipeline with a different PDF and a different prompt:

```bash
python etl.py --pdf data/invoice-sample.pdf --prompt prompts/extract_invoice.txt
```

Open `data/output.json` again. You now have **two records** — one meeting agenda extraction and one invoice extraction. Same pipeline, different inputs, different structured output.

This is the core idea of ETL: a repeatable process that turns unstructured data into a structured database.

---

## Step 8: See How Changing the Prompt Changes the Output

You treat the prompt as a product. Small changes can make large differences. You are going to modify the prompt and re-run the pipeline to see how the output changes.

### Try it

1. Open `prompts/extract_meeting.txt` in your editor.
2. In the `<output_schema>` section, add a new field: `"total_agenda_items": "number"`.
3. In the `<instructions>` section, add a step: "6. Count the total number of agenda items across all sections."
4. Save the file.
5. Re-run:

```bash
python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/extract_meeting.txt
```

Check the terminal output — your new field should appear in the JSON. Open `data/output.json` and compare record #1 (before your change) to record #3 (after).

**This is prompt engineering.** You did not change any Python code. You changed a text file and the LLM produced different structured output.

---

## Step 9: See How Changing Temperature Changes the Output

1. Open `config.json`.
2. Change `"temperature": 0.0` to `"temperature": 1.0`.
3. Run the meeting extraction again:

```bash
python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/extract_meeting.txt
```

4. Run it a second time.
5. Compare the two new records in `data/output.json`.

At temperature 0.0, the output is nearly identical every run. At 1.0, you will see variation — different wording in titles, possibly different items extracted.

**For ETL/data extraction, you almost always want temperature 0.0** — consistency and accuracy matter more than creativity.

Set it back to 0.0 when you are done:

```json
"temperature": 0.0
```

---

## Step 10: Write Your Own Prompt

Create a new file `prompts/my_prompt.txt`. Use this skeleton:

```
You are a [role description].

<document>
{{PAYLOAD}}
</document>

<rules>
- Return ONLY valid JSON. No markdown, no explanations.
- [Your rules here]
</rules>

<instructions>
Think through this step by step:
1. [First thing to look for]
2. [Second thing to look for]
3. Assemble the final JSON object.
</instructions>

<output_schema>
{
  "your_field": "type",
  "another_field": "type"
}
</output_schema>

<example>
Input: [Brief description of example input]
Output:
{
  "your_field": "example value"
}
</example>
```

Run it:

```bash
python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/my_prompt.txt
```

---

## Step 11: Try a Different Model

1. List available models from the command line:

```bash
aws bedrock list-foundation-models --region us-west-2 --profile default --query "modelSummaries[?contains(providerName, 'Anthropic')].{Id:modelId, Name:modelName}" --output table
```

2. Pick a different model ID from the list.
3. Open `config.json` and replace the `model_id` value.
4. Re-run the pipeline and compare the output quality, speed, and cost.

---

## How the Script Works (For Reference)

Open `etl.py` and read through it. The entire pipeline is about 90 lines of Python with three functions:

| Function | What It Does |
|----------|-------------|
| `extract_text(pdf_path)` | Opens the PDF with `pdfplumber`, pulls text from every page, returns a single string. |
| `transform(text, prompt_path, config)` | Loads the prompt template, replaces `{{PAYLOAD}}` with the text, builds the Bedrock API payload, calls `invoke_model`, parses the JSON response. |
| `load(record, output_path)` | Reads the existing `output.json` array (or creates one), appends the new record, writes it back. |

### Key code to understand

**The API call:**
```python
session = boto3.Session(profile_name=config["profile_name"])
client = session.client("bedrock-runtime", region_name=config["region"])

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": config["max_tokens"],
    "temperature": config["temperature"],
    "messages": [{"role": "user", "content": prompt}],
}

response = client.invoke_model(
    modelId=config["model_id"],
    body=json.dumps(body),
)
```

This is the same Bedrock `invoke_model` call pattern from the invoking-models module — but here the "message" is an entire engineered prompt with a document injected into it.

**The variable injection:**
```python
template = open(prompt_path).read()
prompt = template.replace("{{PAYLOAD}}", text)
```

Two lines. The raw PDF text gets dropped into the prompt template wherever `{{PAYLOAD}}` appears. This is how you programmatically inject variables into a well-engineered prompt.

---

## Quick Reference

| Task | Command |
|------|---------|
| Clone the repo | `git clone https://github.com/cal-poly-dxhub/generative-ai-learning.git` |
| Sign in to AWS | `aws sso login --profile default` |
| Verify identity | `aws sts get-caller-identity --profile default` |
| Install dependencies | `pip install boto3 pdfplumber` |
| Run meeting extraction | `python etl.py --pdf data/Board-of-Supervisors-Agenda.pdf --prompt prompts/extract_meeting.txt` |
| Run invoice extraction | `python etl.py --pdf data/invoice-sample.pdf --prompt prompts/extract_invoice.txt` |
| Run custom prompt | `python etl.py --pdf data/your-file.pdf --prompt prompts/my_prompt.txt` |
| Check output | Open `data/output.json` |

## Troubleshooting

| Error | Solution |
|-------|----------|
| `The SSO session associated with this profile has expired` | Run `aws sso login --profile default` again |
| `ProfileNotFound` | Update `profile_name` in `config.json` to match your AWS CLI profile |
| `No module named 'pdfplumber'` | Run `pip install pdfplumber`. If using a venv, make sure it is activated. |
| `AccessDeniedException when calling Bedrock` | Your IAM role may not have Bedrock permissions. Contact your admin. |
| `[EXTRACT] Got 0 characters` | The PDF may be a scanned image, not searchable text. Use a text-based PDF. |
| `[TRANSFORM] Warning: response was not valid JSON` | Check the raw output in terminal. Your prompt may need to be more explicit about returning only JSON. |
