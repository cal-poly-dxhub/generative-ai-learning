import boto3
import json

# =============================================================================
# Exploring LLM Parameters: Temperature, Top K, and Top P
#
# When you call an LLM, you can tune HOW it generates text by adjusting
# sampling parameters. These control the randomness and creativity of the
# model's output.
#
# - Temperature: Controls overall randomness. Lower = more focused and
#   deterministic. Higher = more creative and varied.
#
# - Top K: Limits the model to choosing from only the K most likely next
#   words at each step. Lower K = more predictable. Higher K = more variety.
#
# - Top P (nucleus sampling): Instead of a fixed count, picks from the
#   smallest set of words whose combined probability adds up to P.
#   Lower P = fewer choices = more focused. Higher P = more choices.
# =============================================================================

MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
REGION = "us-west-2"


def call_with_parameters(message: str, temperature: float = 1.0,
                         top_k: int = None, top_p: float = None):
    """Call Bedrock with specific sampling parameters.

    Args:
        message: The prompt to send to the model.
        temperature: Controls randomness (0.0 = deterministic, 1.0 = default).
        top_k: Only consider the top K most likely tokens at each step.
        top_p: Only consider tokens within the top P cumulative probability.
    """
    client = boto3.client("bedrock-runtime", region_name=REGION)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": message}],
    }

    # The API does not allow temperature and top_p at the same time.
    # Only include temperature when top_p is not specified.
    if top_p is not None:
        payload["top_p"] = top_p
    else:
        payload["temperature"] = temperature
    if top_k is not None:
        payload["top_k"] = top_k

    response = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(payload)
    )

    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"]


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_example(label: str, result: str):
    """Print a labeled example result."""
    print(f"\n--- {label} ---")
    print(result)


# =============================================================================
# Example 1: Temperature
#
# Temperature is the most commonly used parameter. It scales the probability
# distribution the model uses to pick the next word.
#
#   - temperature=0.0  -> Always picks the most likely word. The output is
#                         nearly identical every time you run it.
#   - temperature=1.0  -> Default behavior. A good balance of coherence
#                         and variety.
#   - temperature close to 1.0 -> More randomness. The model explores less
#                         likely words, leading to more creative (but
#                         sometimes less coherent) output.
#
# When to use low temperature:  Factual Q&A, code generation, math problems.
# When to use high temperature: Creative writing, brainstorming, poetry.
# =============================================================================

def example_temperature():
    print_section("TEMPERATURE: How randomness affects output")

    prompt = "Write a one-sentence description of the ocean."

    # Low temperature: focused and consistent
    print("\nPrompt:", prompt)
    print("(We call the model 3 times at each temperature to show variation)\n")

    print("--- Temperature = 0.0 (deterministic, no randomness) ---")
    for i in range(1, 4):
        result = call_with_parameters(prompt, temperature=0.0)
        print(f"  Run {i}: {result}")

    # High temperature: creative and varied
    print("\n--- Temperature = 1.0 (default, balanced randomness) ---")
    for i in range(1, 4):
        result = call_with_parameters(prompt, temperature=1.0)
        print(f"  Run {i}: {result}")

    print("\n** Notice how temperature=0.0 gives nearly identical responses,")
    print("   while temperature=1.0 produces different wording each time. **")


# =============================================================================
# Example 2: Top K
#
# At each step, the model calculates a probability for every possible next
# word. Top K limits it to only the K most probable words.
#
#   - top_k=1   -> Only the single most likely word. Very deterministic.
#   - top_k=10  -> Choose from the top 10 most likely words.
#   - top_k=250 -> A wide pool of candidates, more variety.
#
# Think of it like choosing a restaurant: top_k=1 means you always go to
# your favorite. top_k=10 means you pick from your top 10. top_k=250 means
# you'd consider almost anywhere in town.
# =============================================================================

def example_top_k():
    print_section("TOP K: Limiting the word choices")

    prompt = "List 5 creative names for a pet goldfish."

    print("\nPrompt:", prompt, "\n")

    print("--- Top K = 1 (only the most likely next word) ---")
    for i in range(1, 3):
        result = call_with_parameters(prompt, top_k=1)
        print(f"  Run {i}: {result}\n")

    print("--- Top K = 100 (choose from top 100 words at each step) ---")
    for i in range(1, 3):
        result = call_with_parameters(prompt, top_k=100)
        print(f"  Run {i}: {result}\n")

    print("** With top_k=1, you get very predictable names.")
    print("   With top_k=100, the model has more freedom to surprise you. **")


# =============================================================================
# Example 3: Top P (Nucleus Sampling)
#
# Instead of a fixed number of words, top_p uses probability mass. The model
# considers the smallest set of words whose probabilities add up to at least P.
#
#   - top_p=0.1 -> Only words that together cover 10% of the probability.
#                   Very few choices, very focused output.
#   - top_p=0.9 -> Words covering 90% of the probability. A wide pool.
#
# Top P is adaptive: if the model is very confident about the next word,
# even top_p=0.9 might only include a few options. If the model is uncertain,
# top_p=0.1 could still include several.
# =============================================================================

def example_top_p():
    print_section("TOP P: Probability-based word selection")

    prompt = "Suggest a fun weekend activity."

    print("\nPrompt:", prompt, "\n")

    print("--- Top P = 0.1 (very narrow, only the most probable words) ---")
    for i in range(1, 4):
        result = call_with_parameters(prompt, top_p=0.1)
        print(f"  Run {i}: {result}\n")

    print("--- Top P = 0.95 (wide pool, lots of variety) ---")
    for i in range(1, 4):
        result = call_with_parameters(prompt, top_p=0.95)
        print(f"  Run {i}: {result}\n")

    print("** Low top_p keeps the model on well-trodden paths.")
    print("   High top_p lets it wander into more unique suggestions. **")


# =============================================================================
# Example 4: Combining Parameters for Different Use Cases
#
# In practice, you pick parameter settings based on your goal:
#   - Factual/precise tasks -> low temperature, low top_p or top_k
#   - Creative tasks        -> higher temperature, higher top_p or top_k
# =============================================================================

def example_practical():
    print_section("PRACTICAL: Choosing parameters for different tasks")

    # Use case 1: Factual question -- we want a precise, consistent answer
    factual_prompt = "What is the boiling point of water in Celsius?"
    print("\n-- Factual task (low temperature = 0.0) --")
    print(f"Prompt: {factual_prompt}")
    result = call_with_parameters(factual_prompt, temperature=0.0)
    print_example("Result", result)

    # Use case 2: Creative writing -- we want imaginative, varied output
    creative_prompt = "Write a haiku about a thunderstorm."
    print("\n-- Creative task (temperature = 1.0, top_p = 0.95) --")
    print(f"Prompt: {creative_prompt}")
    print("(Three runs to show variety)\n")
    for i in range(1, 4):
        result = call_with_parameters(creative_prompt, temperature=1.0, top_p=0.95)
        print(f"  Run {i}: {result}\n")


def main():
    print("Exploring LLM Sampling Parameters with AWS Bedrock")
    print("Each example calls the model multiple times so you can")
    print("see how the parameters affect consistency and creativity.\n")

    example_temperature()
    example_top_k()
    example_top_p()
    example_practical()

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("""
  Parameter    | Low Value Effect         | High Value Effect
  -------------|--------------------------|---------------------------
  Temperature  | Focused, deterministic   | Creative, varied
  Top K        | Fewer word choices       | More word choices
  Top P        | Narrow probability pool  | Wide probability pool

  Tips:
  - For factual Q&A or code: use temperature=0.0
  - For creative writing: use temperature=1.0 with top_p=0.9+
  - Top K and Top P both limit choices but in different ways:
    Top K uses a fixed count, Top P uses cumulative probability
  - You typically adjust temperature OR top_p, not both at once
""")


if __name__ == "__main__":
    main()
