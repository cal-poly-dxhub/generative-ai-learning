"""
Embeddings Demo Script
======================
This script demonstrates how text and images can be converted into numerical vectors
(embeddings) and how cosine similarity can be used to measure semantic relatedness.

It compares three text embedding models:
  - spaCy (en_core_web_md): A lightweight, local model with 300-dimensional vectors
  - Amazon Titan (via AWS Bedrock): A cloud-based model with configurable dimensions (up to 1024)
  - Cohere (via AWS Bedrock): A cloud-based model optimized for search and clustering

And one image embedding model:
  - EfficientNet-B0: A pretrained CNN used as a feature extractor for image similarity

Key Concept:
  Embeddings map words, sentences, or images into a high-dimensional vector space where
  semantically similar items are closer together. This enables tasks like search, recommendations,
  and retrieval-augmented generation (RAG).
"""

import boto3
from botocore.config import Config
import json
import os
import numpy as np
from typing import Optional
import spacy
import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import torch.nn.functional as F

## Setup: 
# pip install -r requirements.txt
#  python -m spacy download en_core_web_md  

# =============================================================================
# Utility Functions
# =============================================================================

def cosine_similarity_np(vec1, vec2):
    """
    Calculate cosine similarity between two numpy vectors.

    Cosine similarity measures the angle between two vectors in high-dimensional space.
    - A value of 1.0 means the vectors point in the same direction (identical meaning)
    - A value of 0.0 means the vectors are perpendicular (unrelated)
    - A value of -1.0 means they point in opposite directions (opposite meaning)

    Formula: cos(θ) = (A · B) / (||A|| * ||B||)
    where A · B is the dot product and ||A|| is the magnitude (L2 norm) of vector A.
    """
    dot_product = np.dot(vec1, vec2)       # Sum of element-wise multiplication
    norm_vec1 = np.linalg.norm(vec1)       # Euclidean length of vec1
    norm_vec2 = np.linalg.norm(vec2)       # Euclidean length of vec2
    return dot_product / (norm_vec1 * norm_vec2)


def cosine_similarity_torch(tensor1, tensor2):
    """
    Calculate cosine similarity between two PyTorch tensors.

    Uses PyTorch's built-in F.cosine_similarity which expects batched inputs,
    so we unsqueeze to add a batch dimension of 1. The .item() converts the
    single-element tensor back to a Python float.
    """
    return F.cosine_similarity(tensor1.unsqueeze(0), tensor2.unsqueeze(0)).item()


# =============================================================================
# spaCy Embeddings
# =============================================================================
# spaCy's en_core_web_md model provides 300-dimensional word vectors trained on
# Common Crawl using GloVe. It's fast, runs locally (no API needed), but has
# limited semantic understanding compared to transformer-based models.
# Good for: quick prototyping, single-word comparisons, offline use.
# Limitations: averages word vectors for sentences, misses context/word order.

# Load the spaCy model once at module level to avoid reloading on every call.
# Requires: python -m spacy download en_core_web_md
_nlp = spacy.load("en_core_web_md")


def generate_spacy_vector_embedding(text):
    """
    Generate a vector embedding for the given text using spaCy's medium English model.

    The en_core_web_md model has ~20k unique vectors with 300 dimensions each.
    For multi-word inputs, spaCy averages the individual word vectors together,
    which means it can lose word-order and contextual information.

    Args:
        text: A word or sentence to embed

    Returns:
        A numpy array of shape (300,) representing the text in vector space
    """
    doc = _nlp(text)
    return np.array(doc.vector)


# =============================================================================
# Amazon Titan Embeddings
# =============================================================================
# Amazon Titan Text Embeddings V2 is a transformer-based model hosted on AWS Bedrock.
# It produces embeddings with configurable dimensions (256, 512, or 1024).
# More dimensions = more nuance captured, but also more storage and compute cost.
# Good for: production RAG systems, high-quality semantic search, AWS-native apps.

class TitanEmbeddings(object):
    """
    A callable wrapper around Amazon Titan's embedding model on AWS Bedrock.

    This class handles the API communication with Bedrock, including serializing
    the request body and deserializing the response. It can be used directly as
    a function: embeddings = TitanEmbeddings(); vector = embeddings("hello", 1024)
    """
    accept = "application/json"
    content_type = "application/json"

    def __init__(self, model_id="amazon.titan-embed-text-v2:0", boto3_client=None, region_name='us-west-1'):
        """
        Initialize the Titan embeddings client.

        Args:
            model_id: The Bedrock model identifier for Titan embeddings
            boto3_client: An existing boto3 Bedrock runtime client (optional).
                          If not provided, a new client is created for the specified region.
            region_name: AWS region where Bedrock is available
        """
        if boto3_client:
            self.bedrock_boto3 = boto3_client
        else:
            self.bedrock_boto3 = boto3.client(
                service_name='bedrock-runtime',
                region_name=region_name,
            )
        self.model_id = model_id

    def __call__(self, text, dimensions, normalize=True):
        """
        Generate an embedding vector for the given text.

        Args:
            text: The input text to embed
            dimensions: Number of output dimensions (256, 512, or 1024).
                        Higher = more semantic detail, lower = faster/cheaper.
            normalize: If True, returns a unit vector (length 1.0), which makes
                       cosine similarity equivalent to a simple dot product.

        Returns:
            A list of floats representing the embedding vector
        """
        body = json.dumps({
            "inputText": text,
            "dimensions": dimensions,
            "normalize": normalize
        })
        response = self.bedrock_boto3.invoke_model(
            body=body, modelId=self.model_id, accept=self.accept, contentType=self.content_type
        )
        response_body = json.loads(response.get('body').read())
        return response_body['embedding']


def get_bedrock_client(assumed_role: Optional[str] = None, region: Optional[str] = 'us-west-2',
                       runtime: Optional[bool] = True, external_id=None, ep_url=None):
    """
    Create a boto3 client for Amazon Bedrock with optional configuration overrides.

    This is a flexible factory function that handles several authentication scenarios:
    1. Default credentials (from environment, ~/.aws/credentials, or instance role)
    2. Named AWS profile (set via AWS_PROFILE environment variable)
    3. Assumed IAM role (for cross-account access or elevated permissions)

    Args:
        assumed_role: ARN of an IAM role to assume (for cross-account access)
        region: AWS region (default us-west-2 where Bedrock is available)
        runtime: If True, creates a 'bedrock-runtime' client (for inference/invoke).
                 If False, creates a 'bedrock' client (for model management/listing).
        external_id: External ID for STS AssumeRole (added security for cross-account)
        ep_url: Custom endpoint URL (for VPC endpoints or local testing)

    Returns:
        A boto3 client configured for the Bedrock service
    """
    target_region = region
    session_kwargs = {"region_name": target_region}
    client_kwargs = {**session_kwargs}

    # Check if the user has set an AWS profile (e.g., "dev", "prod") in environment
    profile_name = os.environ.get("AWS_PROFILE")
    if profile_name:
        print(f"  Using profile: {profile_name}")
        session_kwargs["profile_name"] = profile_name

    # Configure retry behavior: up to 10 retries with exponential backoff
    # This handles throttling and transient errors from the Bedrock API
    retry_config = Config(
        region_name=target_region,
        retries={"max_attempts": 10, "mode": "standard"},
    )
    session = boto3.Session(**session_kwargs)

    # If an IAM role ARN is provided, assume that role to get temporary credentials
    # This is common for cross-account access or when running locally but needing
    # production-level permissions
    if assumed_role:
        print(f"  Using role: {assumed_role}", end='')
        sts = session.client("sts")
        if external_id:
            response = sts.assume_role(
                RoleArn=str(assumed_role),
                RoleSessionName="langchain-llm-1",
                ExternalId=external_id
            )
        else:
            response = sts.assume_role(
                RoleArn=str(assumed_role),
                RoleSessionName="langchain-llm-1",
            )
        print(f"Using role: {assumed_role} ... sts::successful!")
        # Override credentials with the temporary ones from STS
        client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
        client_kwargs["aws_secret_access_key"] = response["Credentials"]["SecretAccessKey"]
        client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]

    # 'bedrock-runtime' is for invoking models (generating embeddings, completions)
    # 'bedrock' is for management operations (listing models, getting model info)
    service_name = 'bedrock-runtime' if runtime else 'bedrock'

    if ep_url:
        bedrock_client = session.client(service_name=service_name, config=retry_config, endpoint_url=ep_url, **client_kwargs)
    else:
        bedrock_client = session.client(service_name=service_name, config=retry_config, **client_kwargs)

    return bedrock_client


def generate_titan_vector_embedding(text, embedding_size):
    """
    Generate a vector embedding using Amazon Titan Text Embeddings V2.

    This function creates a Bedrock client, sends the text to the Titan model,
    and returns the resulting embedding as a numpy array.

    Args:
        text: The input text to embed (can be a word, sentence, or paragraph)
        embedding_size: Number of dimensions for the output vector (256, 512, or 1024).
                        1024 gives the highest quality but uses more memory.

    Returns:
        A numpy array of shape (embedding_size,) representing the text in vector space
    """
    aws_client = get_bedrock_client()
    model_id = "amazon.titan-embed-text-v2:0"
    accept = "application/json"
    content_type = "application/json"

    # The Titan model expects a JSON body with the text, desired dimensions,
    # and whether to normalize the output vector to unit length
    body = json.dumps({
        "inputText": text,
        "dimensions": embedding_size,
        "normalize": True  # Unit vector makes cosine similarity = dot product
    })
    response = aws_client.invoke_model(body=body, modelId=model_id, accept=accept, contentType=content_type)
    response_body = json.loads(response.get('body').read())
    return np.array(response_body.get("embedding"))


# =============================================================================
# Cohere Embeddings
# =============================================================================
# Cohere's embed-english-v3 model produces 1024-dimensional embeddings and is
# specifically optimized for different use cases via the "input_type" parameter:
#   - "search_document": for indexing documents in a search system
#   - "search_query": for the user's search query
#   - "classification": for text classification tasks
#   - "clustering": for grouping similar texts together
# Good for: semantic search, clustering, classification tasks.

def generate_cohere_vector_embedding(text_data):
    """
    Generate a vector embedding using Cohere's embed-english-v3 model via Bedrock.

    Cohere's model is particularly good at capturing semantic meaning for search
    and clustering tasks. The "input_type" parameter tells the model how to optimize
    the embedding for the downstream task.

    Args:
        text_data: The input text to embed (single string)

    Returns:
        A numpy array of shape (1024,) representing the text in vector space

    Note:
        The Cohere API accepts an array of texts but we pass a single text
        and return only the first (0th) embedding from the response.
    """
    aws_client = get_bedrock_client()
    input_type = "clustering"  # Optimizes embedding for grouping similar items
    truncate = "NONE"          # Don't truncate input; will error if text is too long
    model_id = "cohere.embed-english-v3"

    # Cohere expects 'texts' as an array, even for a single input
    json_params = {
        'texts': [text_data],
        'truncate': truncate,
        "input_type": input_type
    }
    json_body = json.dumps(json_params)
    params = {'body': json_body, 'modelId': model_id}

    result = aws_client.invoke_model(**params)
    response = json.loads(result['body'].read().decode())
    # Response contains 'embeddings' as a list of lists; we want the first one
    return np.array(response['embeddings'][0])


# =============================================================================
# Image Embeddings (EfficientNet)
# =============================================================================
# EfficientNet-B0 is a convolutional neural network pretrained on ImageNet (1.2M images,
# 1000 classes). By removing the final classification layer, we use it as a feature
# extractor that outputs a 1280-dimensional embedding vector for any input image.
#
# The embedding captures visual features: shapes, textures, colors, spatial relationships.
# Similar-looking images will have similar embeddings, enabling image search and
# comparison without any text labels.

def get_efficientnet_model():
    """
    Load EfficientNet-B0 pretrained on ImageNet and remove the classification head.

    By replacing the classifier with an Identity layer, the model outputs the
    1280-dimensional feature vector from the penultimate layer instead of the
    1000-class probability distribution. This feature vector IS the image embedding.

    We call model.eval() to disable dropout and batch normalization updates,
    since we're using the model for inference only (not training).

    Returns:
        A PyTorch model that outputs 1280-dim embeddings for 224x224 input images
    """
    model = models.efficientnet_b0(pretrained=True)
    model.classifier = torch.nn.Identity()  # Remove the 1000-class output layer
    model.eval()  # Set to evaluation mode (disables dropout, freezes batch norm)
    return model


# Image preprocessing pipeline that matches what EfficientNet was trained on.
# Every image must be transformed identically to how training data was prepared:
#   1. Resize shortest edge to 256px (maintains aspect ratio)
#   2. Center crop to 224x224 (the model's expected input size)
#   3. Convert PIL image to a PyTorch tensor (scales pixel values from 0-255 to 0.0-1.0)
#   4. Normalize with ImageNet's mean and std (the statistics the model learned from)
IMAGE_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


def get_image_embedding(image_path, model):
    """
    Generate a 1280-dimensional embedding vector for an image file.

    The process:
    1. Open the image and convert to RGB (handles grayscale/RGBA inputs)
    2. Apply the preprocessing transforms (resize, crop, normalize)
    3. Add a batch dimension (model expects shape [batch, channels, height, width])
    4. Run forward pass with gradients disabled (faster, uses less memory)
    5. Remove the batch dimension from the output

    Args:
        image_path: Path to the image file (jpg, png, etc.)
        model: The EfficientNet model (from get_efficientnet_model())

    Returns:
        A PyTorch tensor of shape (1280,) representing the image in vector space
    """
    image = Image.open(image_path).convert('RGB')
    input_tensor = IMAGE_TRANSFORM(image).unsqueeze(0)  # Add batch dim: [1, 3, 224, 224]
    with torch.no_grad():  # Disable gradient computation for inference
        embedding = model(input_tensor)
    return embedding.squeeze()  # Remove batch dim: [1280]


# =============================================================================
# Demo Functions
# =============================================================================
# Each demo function below explores a different aspect of embeddings.
# The classic example is the "King - Man + Woman ≈ Queen" analogy, which shows
# that vector arithmetic on embeddings captures semantic relationships.

def run_spacy_demo():
    """
    Demonstrate spaCy embeddings with the classic King/Queen analogy.

    This shows that vector arithmetic works on word embeddings:
    If we take the vector for "King", subtract "man" (removing the male component),
    and add "woman" (adding the female component), we get a vector close to "Queen".

    This works because the embedding space encodes gender as a consistent direction,
    so King-Man+Woman navigates from "male royalty" to "female royalty" in vector space.
    """
    print("=" * 60)
    print("spaCy Embeddings Demo")
    print("=" * 60)

    # Generate embeddings for our four test words
    king_vector = generate_spacy_vector_embedding("King")
    queen_vector = generate_spacy_vector_embedding("Queen")
    man_vector = generate_spacy_vector_embedding("man")
    woman_vector = generate_spacy_vector_embedding("woman")
    print(f"This embedding has {len(king_vector)} dimensions")
    print(f"First 5 values: {king_vector[:5]}")

    # The famous analogy: King - Man + Woman should ≈ Queen
    # This works because the "gender direction" in vector space is consistent
    calculated_queen_vector = king_vector - man_vector + woman_vector

    # How similar are "man" and "woman"? Should be high (both are people/nouns)
    similarity = cosine_similarity_np(man_vector, woman_vector)
    print(f"Cosine Similarity distance man to woman: {similarity:.4f}")

    # How similar are "King" and "Queen"? Should be high (both are royalty)
    similarity = cosine_similarity_np(king_vector, queen_vector)
    print(f"Cosine Similarity distance spaCy King to Queen: {similarity:.4f}")

    # How close is our calculated vector to the actual "Queen" vector?
    # A high value here proves that vector arithmetic captures semantic relationships
    similarity = cosine_similarity_np(calculated_queen_vector, queen_vector)
    print(f"Cosine Similarity distance between spaCy Queen vector and our King - man + woman: {similarity:.4f}")
    print()


def run_titan_demo():
    """
    Same King/Queen analogy test but using Amazon Titan's 1024-dimensional embeddings.

    Titan's transformer-based model should capture more nuanced relationships
    than spaCy's simpler GloVe vectors, but the same arithmetic principle applies.
    More dimensions = more capacity to encode subtle semantic distinctions.
    """
    print("=" * 60)
    print("Amazon Titan Embeddings Demo")
    print("=" * 60)

    king_vector = generate_titan_vector_embedding("King", 1024)
    queen_vector = generate_titan_vector_embedding("Queen", 1024)
    man_vector = generate_titan_vector_embedding("man", 1024)
    woman_vector = generate_titan_vector_embedding("woman", 1024)
    print(f"This embedding has {len(king_vector)} dimensions")

    calculated_queen_vector = king_vector - man_vector + woman_vector

    similarity = cosine_similarity_np(man_vector, woman_vector)
    print(f"Cosine Similarity distance man to woman: {similarity:.4f}")

    similarity = cosine_similarity_np(king_vector, queen_vector)
    print(f"Cosine Similarity distance Titan King to Queen: {similarity:.4f}")

    similarity = cosine_similarity_np(calculated_queen_vector, queen_vector)
    print(f"Cosine Similarity distance between Titan Queen vector and our King - man + woman: {similarity:.4f}")
    print()


def run_cohere_demo():
    """
    Same King/Queen analogy test using Cohere's embed-english-v3 model.

    Cohere's model is specifically trained for semantic similarity tasks,
    so it may show different patterns in the analogy test compared to
    general-purpose models like spaCy or Titan.
    """
    print("=" * 60)
    print("Cohere Embeddings Demo")
    print("=" * 60)

    king_vector = generate_cohere_vector_embedding("King")
    queen_vector = generate_cohere_vector_embedding("Queen")
    man_vector = generate_cohere_vector_embedding("man")
    woman_vector = generate_cohere_vector_embedding("woman")
    print(f"This embedding has {len(king_vector)} dimensions")
    print(f"First 5 values: {king_vector[:5]}")

    calculated_queen_vector = king_vector - man_vector + woman_vector

    similarity = cosine_similarity_np(man_vector, woman_vector)
    print(f"Cosine Similarity distance man to woman: {similarity:.4f}")

    similarity = cosine_similarity_np(king_vector, queen_vector)
    print(f"Cosine Similarity distance Cohere King to Queen: {similarity:.4f}")

    similarity = cosine_similarity_np(calculated_queen_vector, queen_vector)
    print(f"Cosine Similarity distance between Cohere Queen vector and our King - man + woman: {similarity:.4f}")
    print()


def run_comparison_demo():
    """
    Compare all three models on increasingly complex inputs to see how they differ.

    Tests:
    1. "cat" vs "book" - Two unrelated nouns (expect low similarity)
    2. Two sentences describing the same scene with different words (expect high similarity
       from models that understand meaning, not just word overlap)
    3. Surfing vs snowboarding - Related activities with shared themes but different domains
       (expect moderate similarity; good models capture the shared "board sport flow state")
    4. Random nonsense sentences - No semantic overlap (expect very low similarity)

    Key insight: More capable models (Titan, Cohere) should show higher similarity for
    semantically related content and lower similarity for unrelated content, giving
    better separation. spaCy struggles with sentences because it just averages word vectors.
    """
    print("=" * 60)
    print("Cross-Model Comparison")
    print("=" * 60)

    # --- Test 1: Simple unrelated words ---
    # "cat" and "book" are both common nouns but semantically unrelated.
    # We expect low similarity scores across all models.
    print("\n--- cat vs book ---")
    similarity = cosine_similarity_np(generate_titan_vector_embedding("cat", 1024), generate_titan_vector_embedding("book", 1024))
    print(f"Cosine Similarity of cat to book using Titan: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_cohere_vector_embedding("cat"), generate_cohere_vector_embedding("book"))
    print(f"Cosine Similarity of cat to book using Cohere: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_spacy_vector_embedding("cat"), generate_spacy_vector_embedding("book"))
    print(f"Cosine Similarity of cat to book using spaCy: {similarity:.4f}")

    # --- Test 2: Same meaning, completely different vocabulary ---
    # Both sentences describe: city skyscrapers reflecting sunset + busy streets with diverse people.
    # A model that truly understands semantics should rate these as highly similar despite
    # having almost no words in common (e.g., "skyscrapers" vs "high-rises", "gleaming" vs "polished").
    sentence1 = "The majestic, towering skyscrapers, their gleaming windows reflecting the golden rays of the setting sun, stood as a testament to human ingenuity and the indomitable spirit of progress, while the bustling streets below teemed with life as people from all walks of life hurried to their destinations, their faces a mix of determination and weariness, yet each individual contributing to the vibrant tapestry of the city's existence."
    sentence2 = "The awe-inspiring, colossal high-rises, their polished glass facades mirroring the warm, amber glow of the fading daylight, served as a powerful symbol of human innovation and the unyielding drive for advancement, as the lively thoroughfares beneath pulsed with energy, filled with individuals from diverse backgrounds rushing to their intended locations, their expressions an amalgamation of resolve and fatigue, yet all playing a vital role in the dynamic, intricate mosaic that shaped the city's vibrant identity."

    print("\n--- Semantically similar sentences (different words) ---")
    similarity = cosine_similarity_np(generate_spacy_vector_embedding(sentence1), generate_spacy_vector_embedding(sentence2))
    print(f"Cosine Similarity using spaCy: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_titan_vector_embedding(sentence1, 1024), generate_titan_vector_embedding(sentence2, 1024))
    print(f"Cosine Similarity using Titan: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_cohere_vector_embedding(sentence1), generate_cohere_vector_embedding(sentence2))
    print(f"Cosine Similarity using Cohere: {similarity:.4f}")

    # --- Test 3: Related activities (surfing vs snowboarding) ---
    # These share thematic elements: board sports, flow state, nature, freedom, physical sensation.
    # But they describe very different environments (ocean vs mountain, warm vs cold).
    # Good models should capture the thematic similarity while noting the differences.
    surfing = "Surfing is an experience that blends adrenaline, tranquility, and connection with nature in a way that's hard to put into words but unforgettable once you feel it. Imagine paddling out through the rhythm of the ocean, the sun warming your back, saltwater clinging to your skin. You wait just beyond the breakers, scanning the horizon for the right wave\u2014a moment of stillness, of anticipation. When it comes, you turn your board toward shore, paddle hard, and feel the lift as the wave catches you. Then you pop up\u2014feet planted, knees bent, arms out\u2014and suddenly, you're riding a force of nature. The board glides effortlessly as the wave curls behind you. There's a split second where everything aligns: your balance, the speed, the sound of rushing water, and the pure exhilaration of being carried by the ocean. Every ride is different. Some are smooth and easy, others fast and wild. Sometimes you wipe out\u2014tossed and tumbled underwater, lungs burning, trying to find the surface. But even that feels part of the magic. It's humbling. It teaches respect. Surfing isn't just a sport. It's a state of mind. It's patience and persistence. It's the joy of catching your first wave or the meditative calm of floating on your board, just watching the sun dip below the horizon."
    snowboarding = "Snowboarding on fresh powder is pure freedom\u2014like floating, flying, and dancing all at once. The moment your board hits untouched snow, everything changes. It's soft, silent, and surreal. Instead of the usual hardpack chatter under your feet, there's this quiet swoosh as you carve through the fluff. Each turn feels like slicing through silk. Your board sinks just a little, giving you that surfy, weightless feeling, like you're gliding above the ground. You lean back slightly to stay afloat, and with each movement, you're not just riding the mountain\u2014you're flowing with it. The powder cushions every bump and fall, making the ride forgiving and playful. The world around you goes quiet\u2014muffled by the snow\u2014so all you hear is the wind in your ears and the sound of your own breath. Trees blur past, sunlight catches on snowflakes in the air, and your legs start to burn as you float turn after turn, not wanting it to end. It's the kind of ride that leaves your heart pounding and your face aching from grinning so hard. The first tracks you lay through fresh powder? They're yours alone\u2014like signing your name on nature."

    print("\n--- Surfing vs Snowboarding ---")
    similarity = cosine_similarity_np(generate_titan_vector_embedding(surfing, 1024), generate_titan_vector_embedding(snowboarding, 1024))
    print(f"Cosine Similarity using Titan: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_spacy_vector_embedding(surfing), generate_spacy_vector_embedding(snowboarding))
    print(f"Cosine Similarity using spaCy: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_cohere_vector_embedding(surfing), generate_cohere_vector_embedding(snowboarding))
    print(f"Cosine Similarity using Cohere: {similarity:.4f}")

    # --- Test 4: Random nonsense with no semantic overlap ---
    # These sentences are grammatically correct but semantically absurd and unrelated.
    # We expect the lowest similarity scores here. If a model gives a high score,
    # it might be overfitting on syntactic patterns rather than true meaning.
    s1 = "The giraffe wore a monocle while arguing with a squirrel about the ethics of pancake toppings."
    s2 = "A forgotten shoelace fluttered quietly on a moonlit battlefield, untouched by time or tennis."

    print("\n--- Random nonsense sentences ---")
    similarity = cosine_similarity_np(generate_spacy_vector_embedding(s1), generate_spacy_vector_embedding(s2))
    print(f"Cosine Similarity using spaCy: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_titan_vector_embedding(s1, 1024), generate_titan_vector_embedding(s2, 1024))
    print(f"Cosine Similarity using Titan: {similarity:.4f}")
    similarity = cosine_similarity_np(generate_cohere_vector_embedding(s1), generate_cohere_vector_embedding(s2))
    print(f"Cosine Similarity using Cohere: {similarity:.4f}")
    print()


def run_image_demo():
    """
    Demonstrate image embeddings using EfficientNet-B0 as a feature extractor.

    We compare four images:
    - House Sparrow (small brown bird)
    - Black Phoebe (small dark bird, different species)
    - White-crowned Sparrow (another sparrow species, visually similar to house sparrow)
    - Fork (a piece of silverware, completely different category)

    Expected results:
    - Two sparrow species should have the HIGHEST similarity (similar shape, color, size)
    - Two different birds should have moderate-to-high similarity (both are birds)
    - Bird vs fork should have the LOWEST similarity (completely different objects)

    This demonstrates that image embeddings capture visual features (shape, texture, color)
    in a way that clusters semantically similar objects together in vector space.
    """
    print("=" * 60)
    print("Image Embeddings Demo (EfficientNet)")
    print("=" * 60)

    # Load the model once and reuse it for all images (much faster than reloading)
    model = get_efficientnet_model()

    # Generate 1280-dimensional embeddings for each image
    fork_emb = get_image_embedding('./images/fork.jpg', model)
    sparrow_emb = get_image_embedding('./images/sparrow.jpg', model)
    phoebe_emb = get_image_embedding('./images/phoebe.jpg', model)
    white_crown_emb = get_image_embedding('./images/whitecrown.jpg', model)

    # Compare: two birds of different species (moderate-high similarity expected)
    similarity = cosine_similarity_torch(sparrow_emb, phoebe_emb)
    print(f"Cosine similarity between two different birds: {similarity:.4f}")

    # Compare: bird vs non-bird object (low similarity expected)
    similarity = cosine_similarity_torch(sparrow_emb, fork_emb)
    print(f"Cosine similarity between the fork and the sparrow: {similarity:.4f}")

    # Compare: two sparrow species (highest similarity expected - most visually similar)
    similarity = cosine_similarity_torch(sparrow_emb, white_crown_emb)
    print(f"Cosine similarity between the white crown sparrow and house sparrow: {similarity:.4f}")
    print()


# =============================================================================
# Entry Point
# =============================================================================
# When run as a script (not imported), execute all demos in sequence.
# Each demo is independent and can be commented out if you only want to test
# specific models (e.g., skip Titan/Cohere demos if you don't have AWS access).

if __name__ == "__main__":
    print("Running Embeddings Demo")
    print()

    # Run each demo section - comment out any you want to skip
    run_spacy_demo()          # Local model, no API needed (requires: python -m spacy download en_core_web_md)

    input("Hit return to run next demo...")
    run_titan_demo()          # Requires AWS credentials with Bedrock access

    input("Hit return to run next demo...")
    run_cohere_demo()         # Requires AWS credentials with Bedrock access

    input("Hit return to run next demo...")
    run_comparison_demo()     # Requires all three models

    input("Hit return to run next demo...")
    run_image_demo()          # Local model, no API needed (downloads weights on first run)
