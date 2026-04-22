"""
HyDE (Hypothetical Document Embeddings) — Advanced Retrieval Strategy
=====================================================================
This script demonstrates the HyDE technique for improving RAG retrieval quality.

The Problem:
  A user's question is typically short ("What is the latest research for broken ribs
  in children"), while the stored documents are long, detailed paragraphs with domain
  terminology. Short queries and long documents live in different parts of embedding
  space, so cosine similarity between them may be weak even when the document is relevant.

The HyDE Solution:
  Before embedding the query, ask an LLM to generate a hypothetical answer — a fake
  document that reads like the kind of article that WOULD answer the question. This
  hypothetical document has much more semantic overlap with the real stored documents,
  so embedding it produces a vector that lands closer to relevant results.

Pipeline comparison:
  Standard:  query -> embed(query) -> search
  HyDE:     query -> LLM generates fake answer -> embed(fake answer) -> search

The tradeoff is one extra LLM call per query, but the retrieval quality improvement
can be dramatic — especially when queries are short and documents are technical.
"""

import boto3
import json
import os
import time
import numpy as np
import pandas as pd


# =============================================================================
# Setup
# =============================================================================
# AWS Bedrock client — credentials come from exported environment variables.
_aws_client = boto3.client(service_name="bedrock-runtime", region_name="us-west-2")


# =============================================================================
# Utility Functions
# =============================================================================

def clean_value(value):
    """
    Remove non-alphanumeric characters (except spaces) from text.
    Simple cleaning step for raw CSV data.
    """
    value_str = str(value)
    return ''.join(char for char in value_str if char.isalnum() or char.isspace())


def cosine_similarity(vec1, vec2):
    """
    Calculate cosine similarity between two numpy vectors.

    Formula: cos(θ) = (A · B) / (||A|| * ||B||)
    Returns a value between -1.0 and 1.0 where 1.0 = identical meaning.
    """
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    return dot_product / (norm_vec1 * norm_vec2)


# =============================================================================
# Embedding Function
# =============================================================================
# Direct boto3 call to Amazon Titan — no LangChain.

def generate_titan_vector_embedding(text):
    """
    Generate a 1024-dimensional embedding using Amazon Titan Text Embeddings V2.

    Args:
        text: The text to embed (can be a short query OR a long hypothetical document)

    Returns:
        A numpy array of shape (1024,)
    """
    body = json.dumps({
        "inputText": text,
        "dimensions": 1024,
        "normalize": True
    })
    response = _aws_client.invoke_model(
        body=body,
        modelId="amazon.titan-embed-text-v2:0",
        accept="application/json",
        contentType="application/json"
    )
    response_body = json.loads(response.get('body').read())
    return np.array(response_body['embedding'])


# =============================================================================
# HyDE: Hypothetical Document Generation
# =============================================================================
# This is the core of HyDE — we ask an LLM to generate a fake document that
# WOULD answer the user's question. The key insight is that we never show this
# fake document to the user. We only embed it and use the embedding for search.
#
# We use temperature=1.0 (more creative) because we want the LLM to generate
# rich, domain-specific language that overlaps with real stored documents.

def generate_hyde_response(query_phrase):
    """
    Generate a hypothetical document that would answer the given question.

    Uses Amazon Nova Pro to create a paragraph of text that reads like a real
    article/document answering the question. This hypothetical document will
    have more semantic overlap with the actual stored documents than the
    short original query does.

    The system prompt instructs the LLM to use domain-specific terminology
    (in this case, scientific medical terminology) to maximize embedding
    overlap with the stored research articles.

    Args:
        query_phrase: The user's original question

    Returns:
        A paragraph of hypothetical answer text (string)
    """
    model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 400,
        "temperature": 1.0,
        "system": "You are a helpful assistant.",
        "messages": [
            {
                "role": "user",
                "content": f"Given the following question:\n{query_phrase}\n\n"
                           f"Please generate a paragraph of text that answers the question. "
                           f"Be sure to use scientific medical terminology. "
                           f"Please just include the paragraph in your response."
            }
        ]
    })

    try:
        start_time = time.time()
        response = _aws_client.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        end_time = time.time()
        print(f"  LLM call took: {end_time - start_time:.1f}s")

        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']

    except Exception as e:
        raise RuntimeError(f"HyDE document generation failed: {e}") from e


# =============================================================================
# DataFrame Search
# =============================================================================

def search_dataframe(df, query_vector, top_n=5):
    """
    Search a DataFrame for the most similar rows to a query vector.

    Iterates through every row and computes cosine similarity between the query
    vector and the stored embedding.

    Args:
        df: DataFrame with 'embedded_abstract' column containing numpy arrays
        query_vector: Numpy array representing the embedded query (or HyDE document)
        top_n: Number of top results to return

    Returns:
        A list of (index, similarity_score) tuples, sorted descending
    """
    results = []
    for index, row in df.iterrows():
        article_embedding = row['embedded_abstract']
        results.append((index, cosine_similarity(article_embedding, query_vector)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def load_or_create_embedded_df(csv_path, pickle_path, embed_fn):
    """
    Load pre-computed embeddings from pickle, or create them from the CSV.

    Embedding every article takes several minutes, so results are cached as pickle.
    First run generates the pickle; subsequent runs load it instantly.

    Args:
        csv_path: Path to the source CSV
        pickle_path: Path to save/load the pickle file
        embed_fn: Embedding function to apply to each abstract

    Returns:
        A pandas DataFrame with an 'embedded_abstract' column
    """
    if os.path.exists(pickle_path):
        print(f"Loading cached embeddings from {pickle_path}...")
        return pd.read_pickle(pickle_path)

    print(f"{pickle_path} not found — generating embeddings from {csv_path}...")
    print("  (This may take several minutes on the first run)")
    df = pd.read_csv(csv_path)
    df['abstract'] = df['abstract'].apply(clean_value)

    embeddings = []
    total = len(df)
    for i, abstract in enumerate(df['abstract']):
        embeddings.append(embed_fn(abstract))
        print(f"  Embedded {i + 1}/{total}", end='\r')
    print()
    df['embedded_abstract'] = embeddings

    df.to_pickle(pickle_path)
    print(f"  Saved to {pickle_path}")
    return df


# =============================================================================
# Demo Functions
# =============================================================================

def run_standard_retrieval_demo(dft, query):
    """
    Demo 1: Standard retrieval — embed the raw query and search.

    This is the baseline. The short query "What is the latest research for broken
    ribs in children" gets embedded directly and compared to the article embeddings.

    Notice: the top result may have a decent score, but there's often a large gap
    between #1 and #2, and the overall similarity scores tend to be lower because
    a short question doesn't have much semantic overlap with a detailed abstract.
    """
    print("=" * 60)
    print("Standard Retrieval (No HyDE)")
    print("=" * 60)
    print(f"Query: '{query}'")
    print()

    # Embed the raw query directly
    query_vector = generate_titan_vector_embedding(query)

    results = search_dataframe(dft, query_vector, top_n=5)

    print("Top 5 matching articles:")
    for index, sim_score in results:
        title = dft.iloc[index]['title']
        print(f"  '{title}' — cosine similarity: {sim_score:.4f}")
    print()

    return results


def run_hyde_retrieval_demo(dft, query):
    """
    Demo 2: HyDE retrieval — generate a hypothetical document, embed that, then search.

    The LLM generates a fake article paragraph answering the question. This paragraph
    uses domain-specific vocabulary (medical terminology, scientific phrasing) that
    overlaps much more with the real article abstracts.

    Compare the similarity scores with Demo 1 — HyDE typically produces:
    - Higher cosine similarity for the top result
    - Better separation between relevant and irrelevant results
    - Sometimes surfaces articles that the standard approach missed entirely
    """
    print("=" * 60)
    print("HyDE Retrieval (Hypothetical Document Embeddings)")
    print("=" * 60)
    print(f"Original query: '{query}'")
    print()

    # Step 1: Generate a hypothetical document from the query
    print("Generating hypothetical document...")
    hyde_document = generate_hyde_response(query)
    print(f"\nHypothetical document:\n  {hyde_document[:200]}...")
    print()

    # Step 2: Embed the hypothetical document (NOT the original query)
    print("Embedding the hypothetical document...")
    query_vector = generate_titan_vector_embedding(hyde_document)

    # Step 3: Search using the hypothetical document's embedding
    results = search_dataframe(dft, query_vector, top_n=5)

    print("\nTop 5 matching articles (using HyDE):")
    for index, sim_score in results:
        title = dft.iloc[index]['title']
        print(f"  '{title}' — cosine similarity: {sim_score:.4f}")
    print()

    return results


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    print("Running HyDE (Hypothetical Document Embeddings) Demo")
    print()

    # Load articles with pre-computed Titan embeddings
    dft = load_or_create_embedded_df(
        csv_path='data/latest_research_articles.csv',
        pickle_path='data/embedded_df.pkl',
        embed_fn=generate_titan_vector_embedding
    )
    print(f"Loaded {len(dft)} articles")
    print()

    query = "What is the latest research for broken ribs in children"

    # Run standard retrieval first so we can compare
    standard_results = run_standard_retrieval_demo(dft, query)

    input("Hit return to run HyDE retrieval...")
    hyde_results = run_hyde_retrieval_demo(dft, query)

    # Side-by-side comparison
    print("=" * 60)
    print("Comparison: Standard vs HyDE")
    print("=" * 60)
    print()
    print(f"{'Rank':<6} {'Standard Score':<18} {'HyDE Score':<18}")
    print("-" * 42)
    for i in range(min(len(standard_results), len(hyde_results))):
        std_score = standard_results[i][1]
        hyde_score = hyde_results[i][1]
        print(f"#{i+1:<5} {std_score:<18.4f} {hyde_score:<18.4f}")
    print()
    print("Notice how HyDE typically produces higher similarity scores")
    print("and better separation between relevant and irrelevant results.")
