# Cal Poly AI Summer Camp: Synthetic Student Data Generator

Welcome to our AI Summer Camp! This project will teach you how to use Large Language Models (LLMs) to generate synthetic data for testing and development purposes. You'll learn how to create realistic student records using Python, Amazon Web Services (AWS) Bedrock, and modern data validation techniques.

## Contact Information

**Instructor**: Ryan Gertz - rgertz@calpoly.edu

Feel free to reach out if you have questions about:
- Setting up AWS credentials
- Understanding the code concepts
- Troubleshooting errors
- Ideas for extending this project
- General questions about AI and synthetic data generation

## Video Tutorial
- For a walkthrough of installing VS Code and Python on windows [check this video out](https://drive.google.com/file/d/1hwVswLDUorcEJJz8gbOUracmx9Ufj3QE/view?usp=sharing)

- For a walkthrough of setting up a Virtual Environment with python in VS Code [check this repository out](https://github.com/RyanGertz/ai-summercamp-scripts)

- For a complete walkthrough of this project, check out my video explanation:
[AI Summer Camp Tutorial - Generating Synthetic Data with LLMs](https://drive.google.com/file/d/1gbD7YxdkLRjDaH01TWElBIP94qWS0_zI/view?usp=sharing)

## What You'll Learn

- **Synthetic Data Generation**: Creating realistic fake data for testing and development
- **Large Language Models (LLMs)**: AI systems that can understand and generate structured data
- **AWS Bedrock**: Amazon's service that provides access to powerful AI models
- **Data Validation with Pydantic**: Ensuring generated data meets specific requirements
- **Structured Response Models**: Using type hints and validation to get reliable AI outputs

## What This Code Does

This project demonstrates how to use AI to generate synthetic student records with automatic validation and proper data types. The code:

1. **Defines Data Structure**: Uses Pydantic models to specify exactly what student data should look like
2. **Connects to AWS Bedrock**: Uses the Instructor library with Claude 3.5 Sonnet for structured data generation
3. **Validates Generated Data**: Automatically ensures all data meets requirements (proper formats, value ranges)
4. **Saves Data**: Outputs the validated data to a JSON file for use in other projects

## Prerequisites

Before you start, you'll need:

### 1. Python Installation
- Python 3.9 or higher installed on your computer
- You can download it from [python.org](https://www.python.org/downloads/)
- You can also watch [my video](https://drive.google.com/file/d/1hwVswLDUorcEJJz8gbOUracmx9Ufj3QE/view?usp=drive_link) explaning how to install it on Windows

### 2. AWS Account Setup
- An AWS account
- AWS credentials configured on your computer
- Access to AWS Bedrock service and Claude 3.5 Sonnet model

### 3. Required Python Packages
Install the necessary packages by running this command in your terminal:
```bash
pip install boto3 pydantic instructor
```

## Understanding the Code

### Key Components

**boto3**: Amazon's Python library that lets us connect to AWS services. Think of it as a bridge between your Python code and Amazon's AI models.

**Pydantic**: A Python library that validates data types and ensures data quality. It acts like a strict quality checker for our generated data.

**Instructor**: A library that makes it easy to get structured responses from AI models. Instead of getting plain text back, we get properly formatted data that matches our requirements.


### The Classes Explained

#### Class 1: `Student(BaseModel)`
This class defines what a single student record should look like:
- **Inherits from BaseModel**: This makes it a Pydantic model with automatic validation
- **Field Definitions**: Each attribute specifies the data type and validation rules
- **Descriptions**: Help the AI understand what each field should contain
- **Constraints**: Rules like GPA must be between 2.0-4.0, credits between 0-150

```python
student_id: str = Field(description="Student ID in format STU followed by 6 digits")
# This creates a string field with instructions for the AI
```

#### Class 2: `StudentList(BaseModel)`
This class defines a collection of students:
- **List Type**: Contains multiple Student objects
- **Validation**: Ensures every item in the list is a valid Student
- **Structure**: Provides a clear container for our generated data

### The Functions Explained

#### Function 1: `create_bedrock_client()`
This function sets up our connection to AWS:
- **Creates boto3 client**: Establishes connection to AWS Bedrock in us-west-2 region
- **Wraps with Instructor**: The `instructor.from_bedrock()` adds structured response capabilities
- **Returns configured client**: Ready to make requests that return validated Pydantic models

```python
bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
return instructor.from_bedrock(bedrock_client)
# Instructor wraps the basic AWS client to add structured output capabilities
```

#### Function 2: `generate_synthetic_students(num_students, retries=0)`
This function generates validated student data:
- **Creates client**: Gets our configured Bedrock client
- **Builds prompt**: Constructs detailed instructions for the AI
- **Makes API call**: Sends request to Claude 3.5 Sonnet with `response_model=StudentList`
- **Automatic validation**: Instructor ensures the response matches our StudentList model
- **Error handling**: Retries on throttling errors with exponential backoff

#### Function 3: `main()`
This is the main function that orchestrates everything:
- **Calls generation**: Gets validated StudentList object
- **Converts to JSON**: Uses Pydantic's `model_dump_json()` for clean formatting
- **Saves file**: Writes properly formatted JSON to disk
- **Displays results**: Shows generated student names as confirmation

## How to Run the Code

1. **Save the code**: Copy the code into a file called `synthetic_students.py`

2. **Open your terminal/command prompt**

3. **Navigate to your project folder**:
   ```bash
   cd path/to/your/project
   ```

4. **Run the code**:
   ```bash
   python synthetic_students.py
   ```

5. **Check the output**: Look for the `synthetic_students.json` file in your project folder

## Understanding Pydantic Validation

Pydantic automatically validates all generated data:

### Data Type Validation
- **Strings**: Ensures text fields contain text
- **Dates**: Validates date format and converts strings to Python date objects
- **Floats**: Ensures GPA is a decimal number
- **Integers**: Validates credit counts are whole numbers

### Value Constraints
- **GPA Range**: Must be between 2.0 and 4.0 (`ge=2.0, le=4.0`)
- **Credits Range**: Must be between 0 and 150 (`ge=0, le=150`)
- **Literal Types**: Year must be exactly one of the four specified values
- **Format Requirements**: Field descriptions guide the AI to use proper formats

### Automatic Conversion
- **String dates to date objects**: "2024-01-15" becomes a Python date
- **Number validation**: Ensures GPAs are floats, credits are integers
- **Email format guidance**: Descriptions help AI generate proper email formats


## Understanding the Generated Data

The code generates realistic student records with these validated fields:

- **student_id**: Unique identifier (STU123456) - validated as string
- **first_name/last_name**: Realistic names - validated as strings
- **email**: Properly formatted university email - validated as string
- **date_of_birth**: Birth dates - validated and converted to Python date objects
- **enrollment_date**: When they started school - validated and converted to Python date objects
- **major**: Academic program - validated as string
- **year**: Class standing - validated against literal options only
- **gpa**: Grade point average - validated as float between 2.0-4.0
- **credits_completed**: Academic credits earned - validated as integer between 0-150
- **status**: Current enrollment status - validated against literal options only

## Common Issues and Solutions

### "No credentials found"
This means your AWS credentials aren't set up. You need:
- AWS Access Keys
- AWS CLI configuration
- IAM permissions for Bedrock

### "Access denied to model"
Your AWS account might not have permission to use Claude 3.5 Sonnet:
- Check your AWS Bedrock model access
- Ensure you have the correct model ID: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Verify your IAM permissions

### "Module not found"
Install the required packages:
```bash
pip install boto3 pydantic instructor
```

### "ThrottlingException"
This happens when you make too many requests too quickly:
- The code automatically handles this with retries and exponential backoff
- Wait a few seconds and try again if it persists

### "ValidationError"
This occurs when the AI generates data that doesn't meet our requirements:
- Check which field failed validation in the error message
- The AI usually gets it right, but occasionally needs adjustment
- Consider relaxing constraints if they're too strict

### "Pydantic model validation failed"
The AI generated data that doesn't match our Student model:
- Check if all required fields are present
- Verify data types match expectations
- Review field descriptions for clarity

## Important Notes

- **Cost Awareness**: Each API call to AWS Bedrock costs money (usually just a few cents per request)
- **Rate Limits**: AWS has limits on how many requests you can make per minute
- **Data Privacy**: This generates synthetic data only - no real student information is used
- **Automatic Validation**: Pydantic ensures all data meets requirements before saving
- **Type Safety**: Generated data has proper Python types, not just strings

## Use Cases for Synthetic Data

This type of synthetic data generation is useful for:
- **Testing Applications**: Test your software with realistic, validated data
- **Database Development**: Populate test databases with proper constraints
- **Machine Learning**: Train models with consistent, validated datasets
- **Privacy Protection**: Develop systems without exposing real information
- **API Testing**: Generate data that matches your API schemas

## Getting Help

If you run into issues:
1. Check the error message carefully - Pydantic gives detailed validation errors
2. Ask our camp staff for assistance
3. Look up the specific error message online
4. Try running the code with fewer students first (num_students=1)
5. Check that all required packages are installed

## Resources for Further Learning

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Instructor Library Documentation](https://python.useinstructor.com/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Synthetic Data Reading](https://aws.amazon.com/what-is/synthetic-data/)

---

Happy coding! 🚀
