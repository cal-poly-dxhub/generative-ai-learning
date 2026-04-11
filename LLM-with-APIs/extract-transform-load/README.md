# Cal Poly AI Summer Camp: PDF Document Extraction with AWS Bedrock

Welcome to our AI Summer Camp! This project will teach you how to use Large Language Models (LLMs) to automatically extract and structure information from PDF documents.

## Contact Information

**Instructor**: Ryan Gertz - rgertz@calpoly.edu

Feel free to reach out if you have questions about:
- Setting up AWS credentials
- Understanding document extraction concepts
- Troubleshooting PDF parsing errors
- Ideas for extending this project
- General questions about AI and document processing

## Video Tutorial
- For a walkthrough of installing VS Code and Python on windows [check this video out](https://drive.google.com/file/d/1hwVswLDUorcEJJz8gbOUracmx9Ufj3QE/view?usp=sharing)

- For a walkthrough of setting up a Virtual Environment with python in VS Code [check this repository out](https://github.com/RyanGertz/ai-summercamp-scripts)

- For a complete walkthrough of this project, check out my video explanation:
[AI Summer Camp Tutorial - Text Extraction in Python using LLMs](https://drive.google.com/file/d/1jKaR3tKi2rqzAZ99X3u-GlDZKObKBci0/view?usp=sharing)

## What You'll Learn

- **PDF Text Extraction**: Automatically extracting text content from PDF documents
- **AI-Powered Document Structure**: Using LLMs to identify and organize key information
- **AWS Bedrock**: Leveraging cloud-based AI services for document processing

## What This Code Does

This project demonstrates how to use AI to automatically extract and structure information from PDF documents. The code:

1. **Extracts PDF Text**: Uses pdfplumber to pull text content from PDF files
2. **Structures Information**: Uses LLMs to identify and organize key document elements
3. **Outputs JSON**: Saves structured data in a clean, machine-readable format

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
pip install boto3 pdfplumber
```

### 4. PDF Document
- A PDF file named "Board-of-Supervisors-Agenda.pdf" in your project directory
- Or modify the code to use your own PDF file

## Understanding the Code

### Key Components

**pdfplumber**: A Python library specifically designed for extracting text from PDF documents.

**boto3**: Amazon's Python library that lets us connect to AWS services. Think of it as a bridge between your Python code and Amazon's AI models.

**JSON Output**: JavaScript Object Notation - a standard format for storing and exchanging structured data.

### The Functions Explained

#### Function 1: `extract_text_from_pdf(pdf_file_path: str)`
This function handles PDF text extraction:
- Takes a PDF file path as input
- Uses pdfplumber to open and read the PDF
- Extracts text from each page sequentially
- Returns the combined text content as a single string

#### Function 2: `structure_text_with_llm(text: str)`
This function uses Bedrock to structure the extracted text:
- Takes raw text as input
- Constructs a detailed prompt asking for specific information extraction
- Sends the prompt to LLM via AWS Bedrock
- Returns structured JSON data with meeting details and agenda items

#### Function 3: `main()`
This is the main function that orchestrates the entire process:
- Defines input and output file paths
- Calls the extraction and structuring functions
- Saves the final JSON output to a file

## How to Run the Code

1. **Save the code**: Clone this repo or copy the code into a file called `pdf_extractor.py`

2. **Add your PDF**: Place your PDF file in the same directory and name it "Board-of-Supervisors-Agenda.pdf" (or modify the code to use your filename)

3. **Open your terminal/command prompt**

4. **Navigate to your project folder**:
   ```bash
   cd path/to/your/project
   ```

5. **Run the code**:
   ```bash
   python pdf_extractor.py
   ```

6. **Check the output**: You'll see a new file called `extracted_document.json` with your structured data

## Customizing The Code

### Use Different PDF Files
Modify the file path in the `main()` function:
```python
pdf_file_path = "your-document.pdf"
```

## Understanding the Output

### JSON Structure
The code produces a JSON file with the following structure:
```json
{
  "meeting_title": "BOARD OF SUPERVISORS AGENDA",
  "date": "January 1, 1970",
  "location": "SLO County Government Center",
  "supervisors": [
    {"name": "John Smith", "district": "District 1"},
    {"name": "Jane Doe", "district": "District 2"}
  ],
  "all_section_titles": [
    "Call to Order",
    "Public Comments",
    "Social Services",
    "Transportation"
  ],
  "social_services_items": [
    {
      "item_number": "1",
      "title": "Homeless Services Contract Approval",
      "district": "District Three",
      "type": "Consent"
    }
  ]
}
```

## Common Issues and Solutions

### "No module named 'pdfplumber'"
Install the required package:
```bash
pip install pdfplumber
```

### "File not found" Error
Make sure your PDF file is in the correct location:
- Check the file path in your code
- Verify the PDF file exists in your project directory
- Ensure the filename matches exactly (case-sensitive)

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

### "JSON decode error"
The AI model didn't return valid JSON:
- Check the raw LLM response in the error output
- Simplify your extraction prompt
- Verify your document has the expected structure

## Important Notes

- **Cost Awareness**: Each document processing request costs money (usually a few cents per document)
- **Rate Limits**: AWS has limits on how many requests you can make per minute
- **PDF Quality**: Better quality PDFs (searchable text) produce better results than scanned images
- **Token Limits**: Very large documents may exceed Claude's input limits

## Use Cases for PDF Document Extraction

This type of document processing system is useful for:
- **Government Transparency**: Making public meeting agendas searchable and accessible
- **Legal Document Processing**: Extracting key information from contracts and legal papers
- **Research Automation**: Processing academic papers and research documents
- **Business Intelligence**: Analyzing reports and business documents
- **Compliance Monitoring**: Tracking regulatory documents and requirements

## Getting Help

If you run into issues:
1. Check the error message carefully
2. Verify your PDF file is readable and not corrupted
3. Ask our camp staff for assistance
4. Test with a simpler PDF first
5. Check your AWS credentials and permissions


## Resources for Further Learning

- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [JSON Processing in Python](https://docs.python.org/3/library/json.html)

---

Happy coding! 🚀
