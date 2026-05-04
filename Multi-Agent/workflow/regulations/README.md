# Optional: Bedrock Knowledge Base Setup for State Regulations

The workflow demo works out of the box using built-in regulation stubs. To use real RAG-powered regulation lookup via Amazon Bedrock Knowledge Bases, follow these steps.

## 1. Source Documents

Upload freely available state insurance regulation PDFs to an S3 bucket:

**California:**
- CA Fair Claims Settlement Practices Regulations (Title 10, Chapter 5, Subchapter 7.5)
  - https://www.insurance.ca.gov/01-consumers/130-laws-regs-hearings/05-CCR/fair-claims-regs.cfm
- CA Residential Property Claims Guide (CDI publication)

**Texas:**
- TX Insurance Code Chapter 542 — Processing and Settlement of Claims
  - https://statutes.capitol.texas.gov/Docs/IN/pdf/IN.542.pdf
- TX Consumer Bill of Rights for Homeowners Insurance

**General:**
- NAIC Unfair Trade Practices Act (Model Law 880)

## 2. Create Bedrock Knowledge Base

1. Create an S3 bucket (e.g. `s3://strands-demo-insurance-regs/`)
2. Upload the PDFs
3. In Bedrock console → Knowledge Bases → Create:
   - Name: `insurance-state-regulations`
   - Data source: point to the S3 bucket
   - Embedding model: Amazon Titan Embeddings v2
   - Vector store: default (OpenSearch Serverless)
   - Chunking: default (300 tokens with overlap)
4. Sync the knowledge base

## 3. Configure the Environment

```bash
export KNOWLEDGE_BASE_ID="your-kb-id-here"
# Optionally override the model:
# export BEDROCK_MODEL_ARN="arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0"
```

Then run the workflow as normal — the regulation check agent will use the real KB.
