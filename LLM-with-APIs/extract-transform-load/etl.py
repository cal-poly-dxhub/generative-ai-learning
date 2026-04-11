import boto3
import json
import pdfplumber

def extract_text_from_pdf(pdf_file_path: str):
  """Extract text from PDF using pdfplumber"""
  print(f"Extracting text from {pdf_file_path}...")
  
  extracted_text = ""
  with pdfplumber.open(pdf_file_path) as pdf:
    for page in pdf.pages:
      text = page.extract_text()
      if text:
        extracted_text += text + "\n"
  return extracted_text

def structure_text_with_llm(text: str):
  """Use AWS Bedrock to structure text into JSON"""
  
  client = boto3.client('bedrock-runtime', region_name='us-west-2')

  prompt = f"""
    Please analyze the following document text and extract key information into a structured JSON format.

    Return an object with the following fields:

    - meeting_title
    - date
    - location
    - supervisors (list of names and districts)

    - all_section_titles: a list of all agenda section titles in the document

    - social_services_items: a list of detailed items specifically related to Social Services. These may appear in a section titled "Social Services" or be items that address social services topics such as welfare, benefits, homelessness, housing support, child services, etc.

    Each item in social_services_items should strictly include:
      - item_number
      - title or summary
      - districts (if specified)
      - type (e.g. "Consent", "Public Hearing", "Presentation", etc.)
    do not include anything else for an item. 

    Return only valid JSON. Do not include any explanatory text.

    Document text:
    {text}
    """
  
  body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 8192,
    "messages": [
        {
          "role": "user",
          "content": prompt
        }
    ]
  }
  
  response = client.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    body=json.dumps(body)
  )
  

  response_body = json.loads(response['body'].read())
  llm_output = response_body['content'][0]['text']
  
  try:
    structured_data = json.loads(llm_output)
    return structured_data
  except json.JSONDecodeError:
    return {"raw_llm_response": llm_output}

def main() -> None:
  pdf_file_path = "Board-of-Supervisors-Agenda.pdf"
  output_filename = "extracted_document.json"
  
  try:
    extracted_text = extract_text_from_pdf(pdf_file_path)
    print(f"Extracted {len(extracted_text)} characters of text")
    
    structured_data = structure_text_with_llm(extracted_text)
  
    with open(output_filename, 'w') as file:
      json.dump(structured_data, file, indent=2)

    print(f"Output: {output_filename}")
      
  except Exception as e:
    print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
  main()
