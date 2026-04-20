"""
Chunking Demo Script
====================
This script demonstrates how to break text into smaller, meaningful pieces (chunks)
for use in Retrieval Augmented Generation (RAG) systems.

When feeding data to an LLM, we can't send entire documents at once due to context window
limits. Instead, we chunk documents and retrieve only the most relevant pieces. The quality
of chunking directly impacts retrieval quality.

Three chunking strategies are demonstrated:
  1. Fixed-Size Chunking: Split text into equal-sized token windows with overlap
  2. Sentence-Level Chunking: Group sentences together into chunks
  3. Semantic Chunking: Use embeddings to group semantically related content together

Additionally, spaCy NLP utilities for noun extraction and named entity recognition
are shown as bonus tools for understanding text structure.
"""

import spacy
from sentence_transformers import SentenceTransformer, util


# =============================================================================
# Setup
# =============================================================================
# Load spaCy model once at module level to avoid reloading on every function call.
# en_core_web_md provides tokenization, sentence segmentation, and word vectors.
# Requires: python -m spacy download en_core_web_md
_nlp = spacy.load("en_core_web_md")

# Load SentenceTransformer model for semantic chunking.
# all-MiniLM-L6-v2 is a lightweight model that produces 384-dimensional sentence embeddings.
# It's fast and good enough for similarity comparisons. Downloads weights on first run.
_sentence_model = SentenceTransformer("all-MiniLM-L6-v2")


# =============================================================================
# File Reading
# =============================================================================

def read_file(file_path):
    """
    Read the entire contents of a text file and return as a string.

    Args:
        file_path: Path to the text file to read

    Returns:
        The file contents as a string, or None if the file couldn't be read
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# =============================================================================
# Strategy 1: Fixed-Size Chunking
# =============================================================================
# The simplest approach: split text into chunks of N tokens with optional overlap.
# Overlap ensures that sentences split at chunk boundaries still appear in at least
# one chunk in their entirety (or close to it).
#
# Pros: Simple, predictable chunk sizes, easy to control memory usage
# Cons: May split sentences mid-thought, no awareness of semantic boundaries
# Best for: Small documents, simple use cases, when you need uniform chunk sizes

def fixed_size_chunking(text, chunk_size, overlap):
    """
    Split text into fixed-size token chunks with overlap between consecutive chunks.

    Uses spaCy's tokenizer to split text into tokens (words, punctuation, etc.),
    then groups them into chunks of the specified size. Overlap creates a sliding
    window effect so context isn't completely lost at chunk boundaries.

    Example with chunk_size=5, overlap=2:
      Tokens: [A, B, C, D, E, F, G, H, I, J]
      Chunk 1: [A, B, C, D, E]       (start=0)
      Chunk 2: [D, E, F, G, H]       (start=3, because 5-2=3)
      Chunk 3: [G, H, I, J]          (start=6)

    Args:
        text: The full text to chunk
        chunk_size: Number of tokens per chunk
        overlap: Number of tokens to overlap between consecutive chunks.
                 Higher overlap = more redundancy but less chance of losing context.

    Returns:
        A list of strings, each representing one chunk
    """
    doc = _nlp(text)
    tokens = [token.text for token in doc]

    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk = tokens[start:end]
        chunks.append(" ".join(chunk))
        start += chunk_size - overlap  # move start forward with overlap

    return chunks


# =============================================================================
# Strategy 2: Sentence-Level Chunking
# =============================================================================
# Groups complete sentences together. Respects natural language boundaries
# (periods, question marks, etc.) so chunks always contain whole thoughts.
#
# Pros: Never splits mid-sentence, respects natural boundaries
# Cons: Chunk sizes vary depending on sentence length, no semantic awareness
# Best for: FAQ content, well-structured documents, when sentence integrity matters

def sentence_chunking(text, sentences_per_chunk):
    """
    Split text into chunks where each chunk contains a fixed number of sentences.

    Uses spaCy's sentence segmentation (which understands abbreviations, quotations,
    etc.) to identify sentence boundaries, then groups them into chunks.

    Args:
        text: The full text to chunk
        sentences_per_chunk: How many sentences to include in each chunk.
                            Use 1 for one-sentence-per-chunk (good for FAQs).
                            Use 3-5 for paragraph-like chunks.

    Returns:
        A list of strings, each containing the specified number of sentences
    """
    doc = _nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]

    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk):
        chunk = " ".join(sentences[i:i + sentences_per_chunk])
        chunks.append(chunk)

    return chunks


# =============================================================================
# Strategy 3: Semantic Chunking
# =============================================================================
# The most sophisticated approach: uses sentence embeddings to measure whether
# consecutive text segments are talking about the same topic. When similarity
# drops below a threshold, a new chunk boundary is created.
#
# Pros: Chunks are semantically coherent, adapts to content structure
# Cons: Slower (requires embedding computation), threshold needs tuning
# Best for: High-quality RAG, mixed-topic documents, when retrieval precision matters

def semantic_embedding_chunk(text, threshold):
    """
    Split text into semantically coherent chunks using sentence embeddings.

    Algorithm:
    1. First split text into fixed-size segments (using fixed_size_chunking as a pre-pass)
    2. For each segment, compute its embedding using SentenceTransformer
    3. Compare each new segment's embedding to the current chunk's running average embedding
    4. If similarity >= threshold: add segment to current chunk (same topic)
    5. If similarity < threshold: start a new chunk (topic changed)

    The running average embedding represents the "centroid" of the current chunk's meaning.
    As more segments are added, this centroid shifts. When a new segment is too far from
    the centroid, it signals a topic change.

    Args:
        text: The full text to chunk
        threshold: Cosine similarity threshold (0.0 to 1.0).
                   Lower = larger chunks (more lenient grouping).
                   Higher = smaller chunks (stricter topic coherence).
                   Typical values: 0.3-0.6 depending on content.

    Returns:
        A list of strings, each representing a semantically coherent chunk
    """
    # Pre-split into fixed-size segments to avoid embedding very long passages
    segments = fixed_size_chunking(text, 100, 10)

    chunks = []
    current_chunk_segments = []
    current_chunk_embedding = None

    for segment in segments:
        # Generate embedding for the current segment
        segment_embedding = _sentence_model.encode(segment, convert_to_tensor=True)

        # If starting a new chunk, initialize it with the current segment
        if current_chunk_embedding is None:
            current_chunk_segments = [segment]
            current_chunk_embedding = segment_embedding
        else:
            # Compute cosine similarity between current segment and the chunk's average embedding
            sim_score = util.cos_sim(segment_embedding, current_chunk_embedding)
            if sim_score.item() >= threshold:
                # Same topic: add segment to current chunk and update the running average
                current_chunk_segments.append(segment)
                num_segs = len(current_chunk_segments)
                # Running average: new_avg = (old_avg * (n-1) + new_value) / n
                current_chunk_embedding = ((current_chunk_embedding * (num_segs - 1)) + segment_embedding) / num_segs
            else:
                # Topic changed: finalize current chunk and start a new one
                chunks.append(" ".join(current_chunk_segments))
                current_chunk_segments = [segment]
                current_chunk_embedding = segment_embedding

    # Don't forget the last chunk
    if current_chunk_segments:
        chunks.append(" ".join(current_chunk_segments))

    return chunks


# =============================================================================
# Bonus: spaCy NLP Utilities
# =============================================================================
# spaCy can also extract structured information from text, which can be useful
# for understanding what a document is about before deciding how to chunk it.

def find_nouns(text):
    """
    Extract and print all noun phrases (noun chunks) from the text.

    Noun chunks are "base noun phrases" — flat phrases that have a noun as their head.
    Examples: "the big dog", "world leaders", "machine learning models"

    Useful for: understanding what topics/entities a document discusses,
    building keyword indices, identifying important concepts.

    Args:
        text: The text to analyze
    """
    doc = _nlp(text)
    for noun in doc.noun_chunks:
        print(noun)


def find_entities(text):
    """
    Extract and print all named entities from the text.

    Named entities are real-world objects: people, organizations, locations,
    dates, monetary values, etc. spaCy uses a statistical model to identify these.

    Useful for: understanding document content, building knowledge graphs,
    deciding whether to chunk by entity boundaries.

    Args:
        text: The text to analyze
    """
    doc = _nlp(text)
    for entity in doc.ents:
        print(f"{entity.text} ({entity.label_})")


def _normalize_noun_chunk(span):
    """
    Normalize a noun chunk by lemmatizing and removing determiners/pronouns.

    For example: "the registration process" -> "registration process"
                 "your academic advisor" -> "academic advisor"
                 "classes" -> "class"

    This produces a canonical form for comparison so that "the class" and
    "a class" and "classes" all reduce to the same normalized string.

    Args:
        span: A spaCy Span object (noun chunk)

    Returns:
        A lowercase, lemmatized string with determiners/pronouns stripped
    """
    tokens = [token.lemma_.lower() for token in span
              if token.pos_ not in ("DET", "PRON") and not token.is_space]
    return " ".join(tokens)


def fuzzy_deduplicate(items, similarity_threshold=0.85):
    """
    Remove near-duplicate strings using spaCy's word vectors for fuzzy matching.

    For each new item, we compare its vector to all previously accepted items.
    If it's too similar to something we've already seen (above the threshold),
    we skip it. This gives us a deduplicated list of conceptually unique items.

    The similarity is based on spaCy's built-in .similarity() method which uses
    cosine similarity on the averaged word vectors of each phrase.

    Args:
        items: List of strings to deduplicate
        similarity_threshold: How similar two items must be to count as duplicates.
                              0.85 is a good default — catches "academic advisor" vs
                              "an academic advisor" but keeps "advisor" vs "student" separate.

    Returns:
        A list of unique items (first occurrence kept, near-duplicates removed)
    """
    unique = []
    unique_docs = []

    for item in items:
        item_doc = _nlp(item)
        # Skip items with no vector (rare tokens spaCy doesn't recognize)
        if not item_doc.has_vector or item_doc.vector_norm == 0:
            continue

        is_duplicate = False
        for existing_doc in unique_docs:
            similarity = item_doc.similarity(existing_doc)
            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(item)
            unique_docs.append(item_doc)

    return unique


def get_document_topics(text, similarity_threshold=0.85):
    """
    Extract the key topics from a document by finding noun chunks, normalizing them,
    and fuzzy-deduplicating to remove near-duplicates.

    This gives you a concise overview of what a document is about without the noise
    of repeated phrases like "the process", "the student", "a form", etc.

    Pipeline:
    1. Extract noun chunks via spaCy
    2. Normalize: lemmatize, strip determiners/pronouns
    3. Remove exact duplicates
    4. Fuzzy-deduplicate using vector similarity

    Args:
        text: The full document text
        similarity_threshold: How aggressively to deduplicate (0.85 = moderate)

    Returns:
        A list of unique topic phrases found in the document
    """
    doc = _nlp(text)

    # Normalize all noun chunks
    normalized = [_normalize_noun_chunk(chunk) for chunk in doc.noun_chunks]

    # Remove empty strings and exact duplicates (preserving order)
    seen = set()
    unique_exact = []
    for item in normalized:
        if item and item not in seen:
            seen.add(item)
            unique_exact.append(item)

    # Fuzzy-deduplicate using vector similarity
    unique_fuzzy = fuzzy_deduplicate(unique_exact, similarity_threshold)

    return unique_fuzzy


def get_unique_entities(text, similarity_threshold=0.85):
    """
    Extract named entities from a document and fuzzy-deduplicate them.

    Named entities often repeat with slight variations (e.g., "U.S." vs "United States",
    "Prof. Smith" vs "Professor Smith"). This function collapses those into unique entries.

    Args:
        text: The full document text
        similarity_threshold: How aggressively to deduplicate

    Returns:
        A list of tuples: (entity_text, entity_label) for unique entities
    """
    doc = _nlp(text)

    # Collect entities with their labels, dedup by normalized text first
    entity_map = {}
    for ent in doc.ents:
        key = ent.text.lower().strip()
        if key not in entity_map:
            entity_map[key] = (ent.text, ent.label_)

    # Fuzzy-deduplicate the entity texts
    entity_texts = list(entity_map.keys())
    unique_texts = fuzzy_deduplicate(entity_texts, similarity_threshold)

    # Map back to original text and label
    return [entity_map[t] for t in unique_texts]


# =============================================================================
# Demo Functions
# =============================================================================

def run_fixed_size_demo():
    """
    Demonstrate fixed-size chunking on a sample document.

    Uses 100 tokens per chunk with 20 tokens of overlap. The overlap means
    the last 20 tokens of chunk N appear as the first 20 tokens of chunk N+1,
    ensuring no context is completely lost at boundaries.
    """
    print("=" * 60)
    print("Fixed-Size Chunking Demo")
    print("=" * 60)
    print("Strategy: Split text into 100-token windows with 20-token overlap")
    print()

    chunk_size = 100
    overlap_size = 20

    file_path = "./data/register-for-classes.txt"
    file_content = read_file(file_path)

    if file_content is None:
        print("Unable to read data from file:", file_path)
        return

    chunks = fixed_size_chunking(file_content, chunk_size, overlap_size)

    print(f"Document split into {len(chunks)} chunks (chunk_size={chunk_size}, overlap={overlap_size})")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i + 1} ---\n{chunk}")
    print()


def run_sentence_demo():
    """
    Demonstrate sentence-level chunking on the Declaration of Independence.

    With sentences_per_chunk=1, each sentence becomes its own chunk.
    This is ideal for FAQ-style content where each sentence is a self-contained answer.
    """
    print("=" * 60)
    print("Sentence-Level Chunking Demo")
    print("=" * 60)
    print("Strategy: Each sentence becomes its own chunk")
    print()

    sentences_per_chunk = 1

    file_path = "./data/declaration-of-indep.txt"
    file_content = read_file(file_path)

    if file_content is None:
        print("Unable to read data from file:", file_path)
        return

    chunks = sentence_chunking(file_content, sentences_per_chunk)

    print(f"Document split into {len(chunks)} chunks ({sentences_per_chunk} sentence(s) per chunk)")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i + 1} ---\n{chunk}")
    print()


def run_semantic_demo():
    """
    Demonstrate semantic chunking on a home care document.

    Uses a similarity threshold of 0.45. Segments with similarity above this
    threshold are grouped together (same topic). When similarity drops below,
    a new chunk starts (topic change detected).

    Lower threshold = fewer, larger chunks (more topics grouped together)
    Higher threshold = more, smaller chunks (stricter topic boundaries)
    """
    print("=" * 60)
    print("Semantic Chunking Demo")
    print("=" * 60)
    print("Strategy: Group segments by semantic similarity (threshold=0.45)")
    print()

    file_path = "./data/home-care.txt"
    file_content = read_file(file_path)

    if file_content is None:
        print("Unable to read data from file:", file_path)
        return

    semantic_chunks = semantic_embedding_chunk(file_content, threshold=0.45)

    print(f"Document split into {len(semantic_chunks)} semantic chunks")
    for i, chunk in enumerate(semantic_chunks):
        print(f"\nChunk {i+1}:\n{chunk}\n{'-'*60}")
    print()


def run_nlp_bonus_demo():
    """
    Demonstrate spaCy's noun chunk and named entity extraction, both raw and
    fuzzy-deduplicated to show how deduplication gives a cleaner picture of
    what a document is about.
    """
    print("=" * 60)
    print("Bonus: spaCy NLP Utilities (with Fuzzy Deduplication)")
    print("=" * 60)

    file_path = "./data/register-for-classes.txt"
    file_content = read_file(file_path)

    if file_content is None:
        print("Unable to read data from file:", file_path)
        return

    # First show raw noun chunks (lots of duplicates and noise)
    doc = _nlp(file_content)
    raw_nouns = [chunk.text for chunk in doc.noun_chunks]
    print(f"\n--- Raw Noun Chunks ({len(raw_nouns)} total) ---")
    for noun in raw_nouns[:20]:
        print(f"  {noun}")
    if len(raw_nouns) > 20:
        print(f"  ... and {len(raw_nouns) - 20} more")

    # Now show fuzzy-deduplicated topics (much cleaner)
    topics = get_document_topics(file_content, similarity_threshold=0.85)
    print(f"\n--- Document Topics (fuzzy-deduplicated: {len(topics)} unique) ---")
    for topic in topics:
        print(f"  {topic}")

    # Raw entities vs deduplicated
    raw_entities = [(ent.text, ent.label_) for ent in doc.ents]
    print(f"\n--- Raw Named Entities ({len(raw_entities)} total) ---")
    for text, label in raw_entities[:15]:
        print(f"  {text} ({label})")
    if len(raw_entities) > 15:
        print(f"  ... and {len(raw_entities) - 15} more")

    unique_entities = get_unique_entities(file_content, similarity_threshold=0.85)
    print(f"\n--- Unique Named Entities (fuzzy-deduplicated: {len(unique_entities)}) ---")
    for text, label in unique_entities:
        print(f"  {text} ({label})")
    print()


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    print("Running Chunking Demo")
    print()

    run_fixed_size_demo()

    input("Hit return to run sentence level chunking...")
    run_sentence_demo()

    input("Hit return to run semantic level chunking...")
    run_semantic_demo()

    input("Hit return to run spacey NLP demo...")
    run_nlp_bonus_demo()
