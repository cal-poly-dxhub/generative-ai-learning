# Cal Poly AI Summer Camp: Getting Started with LLMs and AWS Bedrock

Welcome to our AI Summer Camp! This project will teach you how to interact with Large Language Models (LLMs) using Python and Amazon Web Services (AWS). Don't worry if you're new to these technologies!

## Contact Information

**Instructor**: Ryan Gertz - rgertz@calpoly.edu

Feel free to reach out if you have questions about:
- Setting up AWS credentials
- Understanding the code concepts
- Troubleshooting errors
- Ideas for extending this project
- General questions about AI and LLMs

## Video Tutorial

- For a walkthrough of installing VS Code and Python on windows [check this video out](https://drive.google.com/file/d/1hwVswLDUorcEJJz8gbOUracmx9Ufj3QE/view?usp=sharing)

- For a walkthrough of setting up a Virtual Environment with python in VS Code [check this repository out](https://github.com/RyanGertz/ai-summercamp-scripts)

- For a complete walkthrough of this project, check out my video explanation:
[AI Summer Camp Tutorial - Getting Started with AWS Bedrock and Python](https://drive.google.com/file/d/1FwR0wyc6SaYPGWEDihB-d4RRda7D4gcF/view?usp=sharing)

## What You'll Learn

- **Large Language Models (LLMs)**: AI systems that can understand and generate human-like text
- **AWS Bedrock**: Amazon's service that provides access to powerful AI models
- **Python Programming**: Writing code to communicate with AI models
- **API Integration**: How to connect your code to cloud services

## What This Code Does

This project contains two main functions that demonstrate different ways to "talk" to an AI model:

1. **Simple Chat**: Send a question and get a complete answer back
2. **Streaming Chat**: Get the AI's response word-by-word as it's being generated (like ChatGPT's typing effect)

## Prerequisites

Before you start, you'll need:

### 1. Python Installation
- Python 3.7 or higher installed on your computer
- You can download it from [python.org](https://www.python.org/downloads/)
- You can also watch [my video](https://drive.google.com/file/d/1hwVswLDUorcEJJz8gbOUracmx9Ufj3QE/view?usp=drive_link) explaning how to install it on Windows

### 2. AWS Account Setup
- An AWS account
- AWS credentials configured on your computer
- Access to AWS Bedrock service, and associated models

### 3. Required Python Packages
Install the necessary packages by running this command in your terminal:
```bash
pip install boto3
```

## Understanding the Code

### Key Components

**boto3**: This is Amazon's Python library that lets us connect to AWS services. Think of it as a translator between your Python code and Amazon's computers.

**JSON**: A way to format data that both humans and computers can easily read. It's like a universal language for sending information.

**AWS Bedrock**: Amazon's service that hosts various AI models. Instead of running AI models on your own computer (which would be very expensive and slow), you can use Amazon's powerful computers.

### The Two Functions Explained

#### Function 1: `call_bedrock_model(message)`
This function works like sending a text message and waiting for a complete reply:
- You send a question
- The AI thinks about it
- You get the complete answer all at once

#### Function 2: `call_bedrock_model_with_streaming(message)`
This function works like having a real-time conversation:
- You send a question
- The AI starts responding immediately
- You see each word appear as the AI "types" it
- Great for longer responses where you don't want to wait

## How to Run the Code

1. **Save the code**: Copy the code into a file called `bedrock_demo.py`

2. **Open your terminal/command prompt**

3. **Navigate to your project folder**:
   ```bash
   cd path/to/your/project
   ```

4. **Run the code**:
   ```bash
   python bedrock_demo.py
   ```

## Customizing The Code

### Try Different Questions
In the `main()` function, you can change the questions:
```python
# Instead of asking about the US capital, try:
call_bedrock_model("Explain quantum physics in simple terms")
call_bedrock_model_with_streaming("Write a short story about a robot")
```

### Understanding the Models
The code uses two different AI models:
- **Claude 3.5 Sonnet**: Great for complex reasoning and detailed responses
- **Claude 3.5 Haiku**: Faster and more efficient for simpler tasks

## Common Issues and Solutions

### "No credentials found"
This means your AWS credentials aren't set up. Ask for help with:
- AWS Access Keys
- AWS CLI configuration
- IAM permissions

### "Access denied to model"
Your AWS account might not have permission to use Bedrock models. We can help enable access or point out another model.

### "Module not found: boto3"
You need to install the boto3 package:
```bash
pip install boto3
```

## Important Notes

- **Cost Awareness**: Each API call to AWS Bedrock costs money (usually just a few cents)
- **Rate Limits**: AWS has limits on how many requests you can make per minute
- **Content Policies**: AI models have guidelines about what they will and won't discuss


## Getting Help

If you run into issues:
1. Check the error message carefully
2. Ask our camp staff
3. Look up the specific error message online
4. Don't hesitate to experiment - you can't break anything!
   

## Resources for Further Learning

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Python Tutorial for Beginners](https://www.python.org/about/gettingstarted/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

**Remember**: The best way to learn is by doing. Don't be afraid to modify the code and see what happens. Every error is a learning opportunity!

Happy coding! 🚀
