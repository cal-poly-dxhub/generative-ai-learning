import argparse
import boto3
import json
import os
import pdfplumber


def extract_text(pdf_path):
    """Pull raw text from a PDF file."""
    print(f"\n[EXTRACT] Reading PDF: {pdf_path}")
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    print(f"[EXTRACT] Got {len(text)} characters from {len(pdf.pages)} pages")
    return text


def transform(text, prompt_path, config):
    """Inject extracted text into prompt template, call Bedrock, return JSON."""
    # Load prompt template and inject payload
    with open(prompt_path) as f:
        template = f.read()
    prompt = template.replace("{{PAYLOAD}}", text)

    print(f"\n[TRANSFORM] Using prompt template: {prompt_path}")
    print(f"[TRANSFORM] Model: {config['model_id']}  |  Temperature: {config['temperature']}")

    # Build API request
    session = boto3.Session(profile_name=config["profile_name"])
    client = session.client("bedrock-runtime", region_name=config["region"])

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": config["max_tokens"],
        "temperature": config["temperature"],
        "messages": [{"role": "user", "content": prompt}],
    }

    print("[TRANSFORM] Calling Bedrock API...")
    response = client.invoke_model(
        modelId=config["model_id"],
        body=json.dumps(body),
    )

    response_body = json.loads(response["body"].read())
    llm_output = response_body["content"][0]["text"]

    # Strip markdown code fences if present
    cleaned = llm_output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]  # remove opening ```json
        cleaned = cleaned.rsplit("```", 1)[0]  # remove closing ```

    # Parse JSON from response
    try:
        structured = json.loads(cleaned)
        print("[TRANSFORM] Valid JSON received")
    except json.JSONDecodeError:
        print("[TRANSFORM] Warning: response was not valid JSON, storing raw output")
        structured = {"raw_llm_response": llm_output}

    return structured


def load(record, output_path):
    """Append result to a running JSON array file."""
    data = []
    if os.path.exists(output_path):
        try:
            with open(output_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            print("[LOAD] Warning: existing output file was corrupted, starting fresh")
            data = []

    data.append(record)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n[LOAD] Appended record #{len(data)} to {output_path}")


def main():
    # Resolve paths relative to this script's directory, not cwd
    script_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="ETL: PDF -> LLM -> JSON")
    parser.add_argument("--pdf", required=True, help="Path to input PDF")
    parser.add_argument("--prompt", required=True, help="Path to prompt template (.txt)")
    parser.add_argument("--output", default="data/output.json", help="Path to output JSON file (default: data/output.json)")
    parser.add_argument("--config", default="config.json", help="Path to config file (default: config.json)")
    args = parser.parse_args()

    # Resolve relative paths against script directory
    for attr in ("pdf", "prompt", "output", "config"):
        val = getattr(args, attr)
        if not os.path.isabs(val):
            setattr(args, attr, os.path.join(script_dir, val))

    # Load config
    with open(args.config) as f:
        config = json.load(f)

    print("=" * 60)
    print("  ETL PIPELINE: PDF -> Prompt + LLM -> JSON")
    print("=" * 60)

    # 1. Extract
    text = extract_text(args.pdf)

    # 2. Transform
    result = transform(text, args.prompt, config)

    # Preview output
    print(f"\n[PREVIEW] LLM output:")
    print(json.dumps(result, indent=2))

    # 3. Load
    load(result, args.output)

    print("\n" + "=" * 60)
    print("  DONE. Check output file:", args.output)
    print("=" * 60)


if __name__ == "__main__":
    main()
