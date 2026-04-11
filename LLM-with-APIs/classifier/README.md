# Cal Poly AI Summer Camp: Query Classification with Claude

Welcome to our AI Summer Camp! This project will teach you how to use Large Language Models (LLMs) to automatically classify user queries as either "simple" or "complex". You'll learn how to leverage Claude's natural language understanding to build an intelligent query routing system using Python and AWS Bedrock.

## Contact Information

**Instructor**: Ryan Gertz - rgertz@calpoly.edu

Feel free to reach out if you have questions about:
- Setting up AWS credentials
- Understanding query classification concepts
- Troubleshooting errors
- Ideas for extending this project
- General questions about AI and natural language processing

## Video Tutorial
- For a walkthrough of installing VS Code and Python on windows [check this video out](https://drive.google.com/file/d/1hwVswLDUorcEJJz8gbOUracmx9Ufj3QE/view?usp=sharing)

- For a walkthrough of setting up a Virtual Environment with python in VS Code [check this repository out](https://github.com/RyanGertz/ai-summercamp-scripts)

- For a complete walkthrough of this project, check out my video explanation:
[AI Summer Camp Tutorial - Query Classification with AWS Bedrock](https://drive.google.com/file/d/11QMZxRHzoS0YjdmFFbR3yg58rJ3xmlzu/view?usp=sharing)

## What You'll Learn

- **Query Classification**: Automatically categorizing user inputs based on complexity
- **AWS Bedrock**: Using LLMs via the AWS service, Bedrock

## What This Code Does

This project demonstrates how to use AI to automatically classify user queries for intelligent routing. The code:

1. **Connects to AWS Bedrock**: Uses Anthropic's Claude model for natural language understanding
2. **Classifies Queries**: Determines whether a query is "simple" or "complex"
3. **Processes Multiple Queries**: Tests classification on various example queries
4. **Outputs Results**: Displays classification results for analysis

## Prerequisites

Before you start, you'll need:

### 1. Python Installation
- Python 3.7 or higher installed on your computer
- You can download it from [python.org](https://www.python.org/downloads/)
- You can also watch [my video](https://drive.google.com/file/d/1hwVswLDUorcEJJz8gbOUracmx9Ufj3QE/view?usp=drive_link) explaning how to install it on Windows

### 2. AWS Account Setup
- An AWS account
- AWS credentials configured on your computer
- Access to AWS Bedrock service and Anthropic Claude model

### 3. Required Python Packages
Install the necessary packages by running this command in your terminal:
```bash
pip install boto3
```

## Understanding the Code

### Key Components

**boto3**: Amazon's Python library that lets us connect to AWS services. Think of it as a bridge between your Python code and Amazon's AI models.

**Query Classification**: The process of automatically categorizing user inputs based on their complexity, intent, or required processing level.

**Prompt Engineering**: The practice of crafting effective instructions for AI models to get the desired output format and accuracy.

### The Functions Explained

#### Function 1: `classify_query(user_query: str)`
This function sends a query to Claude for classification:
- Takes a user query string as input
- Constructs a detailed prompt with examples and instructions containing the user query
- Sends the prompt to Claude via AWS Bedrock
- Returns either "simple" or "complex" based on the model's analysis

#### Function 2: `main()`
This is the main function that demonstrates the classification system:
- Defines test queries of varying complexity
- Calls the classification function for each query
- Displays the results in a formatted output

## How to Run the Code

1. **Save the code**: Clone this repo or copy the code into a file called `query_classifier.py`

2. **Open your terminal/command prompt**

3. **Navigate to your project folder**:
   ```bash
   cd path/to/your/project
   ```

4. **Run the code**:
   ```bash
   python query_classifier.py
   ```

5. **Check the output**: You'll see classification results printed to the console for each test query

## Customizing The Code

### Add Your Own Test Queries
Modify the test_queries list in the `main()` function:
```python
test_queries = [
    "Your custom query here",
    "Another test question",
    "What is machine learning?",
    "Develop a comprehensive AI strategy for my company"
]
```

### Change Classification Categories
You can modify the prompt to classify queries differently:
```python
prompt = f"""
You are a query classifier. Your job is to classify user queries as either "technical" or "general".

Technical queries involve programming, science, or specialized knowledge:
- "How do I implement a neural network?"
- "Explain quantum computing algorithms"

General queries are everyday questions:
- "What's the weather like?"
- "How do I cook pasta?"

User query: "{user_query}"

Classification (respond with only "technical" or "general"):
"""
```

## Understanding the Output

### Console Output Format
```
Query: 'What is 2+2?'
Classification: simple
--------------------------------------------------
Query: 'Explain the economic impact of artificial intelligence on job markets'
Classification: complex
--------------------------------------------------
```

### Classification Logic
**Simple Queries** typically:
- Ask for basic facts or information
- Can be answered quickly with a direct response
- Don't require extensive analysis or multiple steps
- Examples: "What time is it?", "What is the capital of France?"

**Complex Queries** typically:
- Require detailed explanations or analysis
- Involve multiple steps or considerations
- Need research or synthesis of information
- Examples: "Write a business plan", "Explain quantum physics"

## Common Issues and Solutions

### "No credentials found"
This means your AWS credentials aren't set up. You need:
- AWS Access Keys
- AWS CLI configuration
- IAM permissions for Bedrock

### "Access denied to model"
Your AWS account might not have permission to use Claude:
- Check your AWS Bedrock model access
- Ensure you have the correct model ID
- Verify your IAM permissions

### "Module not found: boto3"
Install the required package:
```bash
pip install boto3
```

### "ValidationException"
This usually means the input is malformed:
- Check that your query strings are not empty
- Ensure proper JSON formatting in the request body
- Verify the model ID is correct

### "Throttling errors"
You're making requests too quickly:
- Add delays between requests
- Reduce the number of test queries
- Consider using a different AWS region

## Important Notes

- **Cost Awareness**: Each classification request costs money (usually fractions of a cent per request)
- **Rate Limits**: AWS has limits on how many requests you can make per minute
- **Prompt Quality**: Better prompts lead to more accurate classifications

## Use Cases for Query Classification

This type of classification system is useful for:
- **Customer Support**: Route simple queries to automated responses, complex ones to human agents
- **Search Systems**: Apply different processing strategies based on query complexity
- **Chatbots**: Determine appropriate response strategies
- **Content Management**: Categorize user-generated content
- **Educational Tools**: Adapt learning materials based on question complexity

## Getting Help

If you run into issues:
1. Check the error message carefully
2. Ask our camp staff for assistance
3. Look up the specific error message online
4. Try running the code with fewer test queries first
5. Verify your AWS credentials are working

## Example Results

After running the code, you might see classifications like:
- "What is 2+2?" → "simple" (basic arithmetic)
- "Explain the economic impact of AI" → "complex" (requires detailed analysis)
- "What color is the sky?" → "simple" (straightforward factual question)
- "Write a marketing strategy" → "complex" (multi-step creative task)


## Resources for Further Learning

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Text Classification Overview](https://developers.google.com/machine-learning/guides/text-classification)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

Happy coding! 🚀
