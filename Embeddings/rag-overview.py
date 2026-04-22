"""
RAG (Retrieval Augmented Generation) Overview
==============================================
This script demonstrates the full RAG pipeline:
  1. Ingest: Read a document, chunk it into pieces, embed each chunk
  2. Store: Save chunks + embeddings in a vector store (pandas DataFrame or SQLite)
  3. Retrieve: Given a user question, embed it and find the most similar chunks
  4. Generate: Send the retrieved chunks + question to an LLM for a grounded answer

Two storage backends are demonstrated:
  - Pandas DataFrame (in-memory, good for small datasets and quick prototyping)
  - SQLite database (persistent, good for larger datasets that should survive restarts)

Embedding models used:
  - Amazon Titan Text Embeddings V2 (via AWS Bedrock)
  - Cohere embed-english-v3 (via AWS Bedrock)

LLM used for answer generation:
  - Anthropic Claude 3 Sonnet (via AWS Bedrock)

No LangChain dependencies — all calls use boto3 directly so you can see
exactly what's happening at each step.
"""

import boto3
import json
import os
import numpy as np
import pandas as pd
import sqlite3
import time

# =============================================================================
# Setup
# =============================================================================
# Create the AWS Bedrock runtime client.
# Credentials come from your environment (export AWS_ACCESS_KEY_ID, etc.)
_aws_client = boto3.client(service_name="bedrock-runtime", region_name="us-west-2")


# =============================================================================
# Utility Functions
# =============================================================================

def limit_string_size(text, max_chars=2048):
    """
    Truncate text to a maximum number of characters.

    Embedding models have input token limits. For example, Cohere embed-english-v3
    supports up to 512 tokens (~2048 characters). Truncating prevents API errors
    when embedding long passages.

    Args:
        text: The input text
        max_chars: Maximum characters to keep (default 2048)

    Returns:
        The original string if short enough, otherwise truncated to max_chars
    """
    if isinstance(text, str):
        return text[:max_chars]
    return text


def clean_value(value):
    """
    Remove non-alphanumeric characters (except spaces) from text.

    This is a simple cleaning step for raw CSV/text data that may contain
    special characters, HTML entities, or other noise that could interfere
    with embedding quality.

    Args:
        value: The value to clean (converted to string first)

    Returns:
        A cleaned string with only letters, numbers, and spaces
    """
    value_str = str(value)
    return ''.join(char for char in value_str if char.isalnum() or char.isspace())


def cosine_similarity(vec1, vec2):
    """
    Calculate cosine similarity between two numpy vectors.

    Cosine similarity measures the angle between two vectors:
      1.0 = identical direction (same meaning)
      0.0 = perpendicular (unrelated)
     -1.0 = opposite direction (opposite meaning)

    Formula: cos(θ) = (A · B) / (||A|| * ||B||)
    """
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    return dot_product / (norm_vec1 * norm_vec2)


# =============================================================================
# Embedding Functions
# =============================================================================
# These functions call AWS Bedrock directly via boto3 (no LangChain).
# Each sends a JSON request to the model and parses the JSON response.

def generate_titan_vector_embedding(text):
    """
    Generate a 1024-dimensional embedding using Amazon Titan Text Embeddings V2.

    Calls the Bedrock API directly. The response contains a normalized unit vector,
    which means cosine similarity is equivalent to a dot product.

    Args:
        text: The text to embed

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


def generate_titan_embedding_as_list(text):
    """
    Same as generate_titan_vector_embedding but returns a plain Python list.

    Some storage backends (like SQLite blob serialization) work better with
    lists than numpy arrays. This avoids an extra conversion step.

    Args:
        text: The text to embed

    Returns:
        A list of 1024 floats
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
    return response_body['embedding']


def generate_cohere_vector_embedding(text_data):
    """
    Generate a 1024-dimensional embedding using Cohere embed-english-v3.

    Cohere's model accepts a list of texts and returns a list of embeddings.
    We pass a single text and return the first (and only) embedding.

    The input is truncated to 2048 characters to stay within the model's token limit.

    Args:
        text_data: The text to embed

    Returns:
        A numpy array of shape (1024,)
    """
    trunc_data = limit_string_size(text_data)
    json_params = {
        'texts': [trunc_data],
        'truncate': "NONE",
        "input_type": "clustering"
    }
    json_body = json.dumps(json_params)
    result = _aws_client.invoke_model(body=json_body, modelId="cohere.embed-english-v3")
    response = json.loads(result['body'].read().decode())
    return np.array(response['embeddings'][0])


# =============================================================================
# Text Chunking
# =============================================================================
# Instead of LangChain's RecursiveCharacterTextSplitter, we use a simple
# character-based chunker. It splits on paragraph boundaries when possible,
# falling back to sentence boundaries, then word boundaries, then raw characters.
# This mimics RecursiveCharacterTextSplitter's behavior with the default separators.

def chunk_text(text, chunk_size=1024, chunk_overlap=256):
    """
    Split text into overlapping chunks, preferring to break at natural boundaries.

    The algorithm tries to split at paragraph breaks (double newline) first,
    then single newlines, then spaces, and finally at the exact character position.
    This avoids splitting words or sentences mid-token when possible.

    Overlap ensures context is preserved across chunk boundaries — the end of one
    chunk overlaps with the beginning of the next.

    Args:
        text: The full text to chunk
        chunk_size: Target size of each chunk in characters (default 1024)
        chunk_overlap: Number of characters to overlap between chunks (default 256)

    Returns:
        A list of text chunks as strings
    """
    separators = ["\n\n", "\n", " ", ""]
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If we're at the end of the text, just take whatever is left
        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Try to find a natural break point near the end of the chunk,
        # preferring paragraph breaks > line breaks > spaces
        split_pos = end
        for sep in separators:
            if not sep:
                break
            # Look for the separator in the last 20% of the chunk
            search_start = start + int(chunk_size * 0.8)
            last_sep = text.rfind(sep, search_start, end)
            if last_sep != -1:
                split_pos = last_sep + len(sep)
                break

        chunk = text[start:split_pos].strip()
        if chunk:
            chunks.append(chunk)

        # Move start forward, accounting for overlap
        start = split_pos - chunk_overlap

    return chunks


# =============================================================================
# Z-Score Filtering
# =============================================================================
# When retrieving chunks, we don't want to just take the "top N" — some queries
# might have 2 highly relevant chunks and 48 irrelevant ones. Z-scores help us
# find the natural cutoff: chunks with z-scores significantly above the mean
# are truly relevant, while those near or below the mean are noise.

def calculate_zscores(cosine_scores):
    """
    Calculate z-scores for a list of cosine similarity scores.

    A z-score tells you how many standard deviations a value is from the mean.
    Positive z-scores = above average similarity (more relevant).
    Negative z-scores = below average similarity (less relevant).

    We use these to dynamically decide how many chunks to include in the context,
    rather than using a fixed "top N" cutoff.

    Args:
        cosine_scores: A list of cosine similarity values

    Returns:
        A list of z-scores, one per input value
    """
    mean = np.mean(cosine_scores)
    std_deviation = np.std(cosine_scores, ddof=1)  # ddof=1 for sample std deviation
    z_scores = [(x - mean) / std_deviation for x in cosine_scores]
    return z_scores


# =============================================================================
# LLM Answer Generation
# =============================================================================
# Calls Claude 3 Sonnet via Bedrock's invoke_model API directly (no LangChain).
# The prompt instructs Claude to answer ONLY from the provided data — no hallucination.

def best_answer(data, question):
    """
    Send retrieved context + user question to Claude and get a grounded answer.

    This is the "Generation" step of RAG. The prompt explicitly tells Claude to:
    - Only use the provided data to answer
    - Not make up information
    - Say "I don't have enough information" if the data doesn't cover the question

    Args:
        data: The concatenated text chunks retrieved by similarity search
        question: The user's original question

    Returns:
        The LLM's answer as a string
    """
    model_id = "us.amazon.nova-pro-v1:0"

    body = json.dumps({
        "inferenceConfig": {
            "max_new_tokens": 2048,
            "temperature": 0.0,
            "top_p": 0.9
        },
        "system": [
            {"text": "You are a helpful assistant that answers questions based on the article data you have been given."}
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"You are to answer the question using only the following data. "
                                f"Do not make up your answer — only use supporting data from the articles. "
                                f"If you don't have enough data, simply respond: "
                                f"'I don't have enough information to answer that question.'\n\n"
                                f"DATA:\n{data}\n\n"
                                f"QUESTION: {question}"
                    }
                ]
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

        response_body = json.loads(response.get('body').read())
        answer = response_body['output']['message']['content'][0]['text']
        print(f"  (LLM response time: {end_time - start_time:.1f}s)")
        return answer

    except Exception as e:
        return f"ERROR generating answer: {e}"


# =============================================================================
# Storage Backend 1: Pandas DataFrame (In-Memory)
# =============================================================================
# The simplest approach — load data into a DataFrame, compute embeddings (or load
# pre-computed ones from pickle), and iterate through rows to find the best matches.
# Good for: small datasets, quick prototyping, demos.
# Limitations: everything in memory, recompute every session, no persistence.

def load_or_create_embedded_df(csv_path, pickle_path, embed_fn):
    """
    Load a pre-computed pickle of embedded articles, or create it from the CSV.

    Embedding every article takes several minutes, so we cache the results as a
    pickle file. On the first run the pickle is generated; subsequent runs load
    it instantly.

    Args:
        csv_path: Path to the source CSV with 'abstract' and 'title' columns
        pickle_path: Path to save/load the pickle file
        embed_fn: The embedding function to apply to each abstract
                  (e.g., generate_titan_vector_embedding or generate_cohere_vector_embedding)

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


def search_dataframe(df, query_vector, top_n=10):
    """
    Search a DataFrame for the most similar rows to a query vector.

    Iterates through every row and computes cosine similarity between the query
    vector and the stored embedding. Returns the top N results sorted by similarity.

    Args:
        df: A pandas DataFrame with an 'embedded_abstract' column containing numpy arrays
        query_vector: A numpy array representing the embedded query
        top_n: Number of top results to return

    Returns:
        A list of (index, similarity_score) tuples, sorted descending by similarity
    """
    results = []
    for index, row in df.iterrows():
        article_embedding = row['embedded_abstract']
        sim = cosine_similarity(article_embedding, query_vector)
        results.append((index, sim))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


# =============================================================================
# Storage Backend 2: SQLite Vector Store (Persistent, Local)
# =============================================================================
# Instead of PostgreSQL + pgvector, we use a local SQLite database. Embeddings are
# stored as binary blobs (serialized numpy arrays). Similarity is computed in Python
# after fetching rows — this keeps the math visible and educational rather than
# hidden behind a SQL operator.
#
# For production use, consider pgvector, Pinecone, Weaviate, or ChromaDB.
# SQLite is used here because it's built into Python — zero setup, zero credentials.

def create_vector_db(db_path="rag_vectors.db"):
    """
    Create (or open) a SQLite database with a table for storing text chunks + embeddings.

    The schema stores:
    - id: Auto-incrementing primary key
    - chunk_text: The raw text of the chunk
    - embedding: The vector embedding stored as a binary blob (serialized numpy array)
    - created_at: Timestamp for when the record was inserted

    Args:
        db_path: Path to the SQLite database file (created if it doesn't exist)

    Returns:
        A sqlite3 Connection object
    """
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def insert_chunk(conn, text, embedding):
    """
    Insert a text chunk and its embedding into the SQLite vector store.

    The numpy embedding array is serialized to raw bytes using tobytes().
    This is compact and fast — a 1024-dim float64 vector is just 8192 bytes.

    Args:
        conn: SQLite connection
        text: The raw text chunk
        embedding: A numpy array or list representing the embedding vector
    """
    embedding_array = np.array(embedding, dtype=np.float64)
    embedding_blob = embedding_array.tobytes()
    conn.execute(
        "INSERT INTO rag_chunks (chunk_text, embedding) VALUES (?, ?)",
        (text, embedding_blob)
    )
    conn.commit()


def fetch_all_chunks(conn):
    """
    Retrieve all chunks and their embeddings from the SQLite vector store.

    Deserializes the binary blobs back into numpy arrays for similarity computation.

    Args:
        conn: SQLite connection

    Returns:
        A list of tuples: (id, chunk_text, embedding_as_numpy_array)
    """
    cursor = conn.execute("SELECT id, chunk_text, embedding FROM rag_chunks")
    rows = []
    for row_id, text, blob in cursor:
        embedding = np.frombuffer(blob, dtype=np.float64)
        rows.append((row_id, text, embedding))
    return rows


def search_similar_chunks(conn, query_embedding, limit=50):
    """
    Find the most similar chunks to a query embedding using cosine similarity.

    This fetches all rows from the database and computes similarity in Python.
    For a production system with millions of rows, you'd want approximate nearest
    neighbor (ANN) search via pgvector, FAISS, or similar. For educational
    datasets (hundreds to low thousands of chunks), this brute-force approach
    works fine and keeps the similarity math completely visible.

    Args:
        conn: SQLite connection
        query_embedding: Numpy array of the query's embedding
        limit: Maximum number of results to return

    Returns:
        A list of (chunk_text, cosine_similarity_score) tuples, sorted descending
    """
    all_chunks = fetch_all_chunks(conn)
    results = []
    for row_id, text, embedding in all_chunks:
        sim = cosine_similarity(embedding, query_embedding)
        results.append((text, sim))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def view_all_data(conn):
    """
    Print a summary of all data stored in the vector database.
    Shows the first 100 characters of each chunk for a quick overview.

    Args:
        conn: SQLite connection
    """
    cursor = conn.execute("SELECT id, chunk_text FROM rag_chunks")
    rows = cursor.fetchall()
    print(f"Total chunks in database: {len(rows)}")
    for row_id, text in rows:
        preview = text[:100].replace('\n', ' ')
        print(f"  [{row_id}] {preview}...")


def purge_all_data(conn):
    """
    Delete all data from the vector store.

    Args:
        conn: SQLite connection
    """
    conn.execute("DELETE FROM rag_chunks")
    conn.commit()
    print("All data purged from vector store.")


def run_similarity_search(question, conn):
    """
    The full retrieval + generation pipeline using the SQLite vector store.

    Steps:
    1. Embed the user's question using Titan
    2. Search the vector store for the top 50 most similar chunks
    3. Calculate z-scores across all similarity scores
    4. Filter to only chunks whose z-score is at least half the top z-score
       (this dynamically selects the "truly relevant" chunks)
    5. Concatenate the selected chunks and send them + the question to Claude

    Args:
        question: The user's natural language question
        conn: SQLite connection to the vector store

    Returns:
        Claude's generated answer based on the retrieved chunks
    """
    query_embedding = generate_titan_vector_embedding(question)
    results = search_similar_chunks(conn, query_embedding, limit=50)

    if not results:
        return "No data found in the vector store."

    # Extract similarity scores for z-score computation
    cosine_scores = [sim for _, sim in results]
    z_scores = calculate_zscores(cosine_scores)

    # Select chunks whose z-score is at least half of the top z-score
    # This is a simple heuristic to find the "elbow" in relevance
    first_z_score = z_scores[0]
    article_text = ""
    for i, (chunk_text, sim_score) in enumerate(results):
        if z_scores[i] > (first_z_score / 2):
            print(f"  Using chunk with cosine similarity: {sim_score:.4f}, z-score: {z_scores[i]:.4f}")
            article_text += chunk_text + "\n"

    if not article_text:
        return "No sufficiently relevant chunks found."

    return best_answer(article_text, question)


# =============================================================================
# Demo Functions
# =============================================================================

def run_dataframe_titan_demo():
    """
    Demo 1: In-memory retrieval using pandas with pre-computed Titan embeddings.

    Loads a CSV of research articles with pre-embedded abstracts (saved as pickle).
    Embeds a user query, computes cosine similarity against all articles,
    and shows the top 10 matches.

    This demonstrates the simplest form of RAG retrieval — no database, just a
    DataFrame and a loop. Good for small datasets and quick experimentation.
    """
    print("=" * 60)
    print("DataFrame Retrieval Demo (Titan Embeddings)")
    print("=" * 60)
    print()

    # Load cached embeddings or generate them from the CSV on first run
    dft = load_or_create_embedded_df(
        csv_path='data/latest_research_articles.csv',
        pickle_path='data/embedded_df.pkl',
        embed_fn=generate_titan_vector_embedding
    )
    print(f"Loaded {len(dft)} articles with Titan embeddings")
    print()

    query = "What is the latest research for broken ribs in children"
    print(f"Query: '{query}'")
    print()

    # Embed the query with the same model used for the articles
    query_vector = generate_titan_vector_embedding(query)

    # Search: compute cosine similarity between query and every article
    results = search_dataframe(dft, query_vector, top_n=10)

    print("Top 10 matching articles:")
    for index, sim_score in results:
        title = dft.iloc[index]['title']
        print(f"  '{title}' — cosine similarity: {sim_score:.4f}")
    print()


def run_dataframe_cohere_demo():
    """
    Demo 2: Same as Demo 1 but using Cohere embeddings.

    Cohere's embed-english-v3 model is specifically optimized for search and
    retrieval tasks, so it may produce different similarity rankings than Titan.
    Comparing the two helps students understand that model choice matters.
    """
    print("=" * 60)
    print("DataFrame Retrieval Demo (Cohere Embeddings)")
    print("=" * 60)
    print()

    # Load cached embeddings or generate them from the CSV on first run
    dfc = load_or_create_embedded_df(
        csv_path='data/latest_research_articles.csv',
        pickle_path='data/cohere_embedded.pkl',
        embed_fn=generate_cohere_vector_embedding
    )
    print(f"Loaded {len(dfc)} articles with Cohere embeddings")
    print()

    query = "What is the latest research for broken ribs in children"
    print(f"Query: '{query}'")
    print()

    # Embed the query with Cohere (must match the model used for the articles)
    query_vector = generate_cohere_vector_embedding(query)

    results = search_dataframe(dfc, query_vector, top_n=10)

    print("Top 10 matching articles:")
    for index, sim_score in results:
        title = dfc.iloc[index]['title']
        print(f"  '{title}' — cosine similarity: {sim_score:.4f}")
    print()


def run_vectordb_demo():
    """
    Demo 3: Full RAG pipeline with SQLite as the vector store.

    This demonstrates the complete end-to-end flow:
    1. Read a document (city staff report)
    2. Chunk it into ~1024-character pieces with 256-character overlap
    3. Embed each chunk with Titan and store in SQLite
    4. Ask a question and retrieve the most relevant chunks using z-score filtering
    5. Send the chunks + question to Claude for a grounded answer

    The SQLite database persists to disk (rag_vectors.db), so you can re-run
    queries without re-embedding. Use purge_all_data() to reset.
    """
    print("=" * 60)
    print("Full RAG Pipeline Demo (SQLite Vector Store)")
    print("=" * 60)
    print()

    db_path = "rag_vectors.db"
    conn = create_vector_db(db_path)

    # Check if data is already loaded (avoid re-embedding on subsequent runs)
    cursor = conn.execute("SELECT COUNT(*) FROM rag_chunks")
    count = cursor.fetchone()[0]

    if count > 0:
        print(f"Found {count} existing chunks in {db_path} — skipping ingestion.")
        print("(Delete rag_vectors.db or call purge_all_data() to re-ingest)")
    else:
        # Step 1: Read the document
        print("Step 1: Reading staff report...")
        with open("data/staff-report.txt", "r") as file:
            text = file.read()
        print(f"  Document length: {len(text)} characters")

        # Step 2: Chunk the document
        print("Step 2: Chunking document...")
        chunks = chunk_text(text, chunk_size=1024, chunk_overlap=256)
        print(f"  Created {len(chunks)} chunks")

        # Step 3: Embed and store each chunk
        print("Step 3: Embedding and storing chunks (this may take a minute)...")
        for i, chunk in enumerate(chunks):
            embedding = generate_titan_embedding_as_list(chunk)
            insert_chunk(conn, chunk, embedding)
            print(f"  Embedded and stored chunk {i + 1}/{len(chunks)}")

    print()

    # Step 4: Review what's in the database
    print("Data in vector store:")
    view_all_data(conn)
    print()

    # Step 5: Ask a question and get a RAG-powered answer
    question = "What will it cost to replace the mixer gearbox?"
    print(f"Question: '{question}'")
    print()
    print("Retrieving relevant chunks...")
    answer = run_similarity_search(question, conn)
    print()
    print("Answer:")
    print(answer)
    print()

    conn.close()


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    print("Running RAG Overview Demo")
    print()

    run_dataframe_titan_demo()

    input("Hit return to run next demo...")
    run_dataframe_cohere_demo()

    input("Hit return to run next demo...")
    run_vectordb_demo()
