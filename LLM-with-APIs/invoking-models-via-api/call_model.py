import boto3
import json


def call_bedrock_model(message: str):
  session = boto3.Session(profile_name="GSB570-BedrockOnly-490332585640")
  client = session.client("bedrock-runtime", region_name="us-west-2")

  payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "messages": [{"role": "user", "content": message}],
  }

  response = client.invoke_model(
    modelId="deepseek.v3.2",
    body=json.dumps(payload)
  )

  response_body = json.loads(response["body"].read())
  #print("Call Model RAW response",response_body)
  return response_body["choices"][0]["message"]["content"]


def call_bedrock_model_with_streaming(message: str):
  session = boto3.Session(profile_name="GSB570-BedrockOnly-490332585640")
  client = session.client("bedrock-runtime", region_name="us-west-2")

  payload = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 4000,
    "messages": [
      {
        "role": "user",
        "content": message
      }
    ]
  })

  response = client.invoke_model_with_response_stream(
    modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
    body=payload
  )

  stream = response.get('body')

  for event in stream:
    chunk = event.get('chunk')
    if not chunk:
      continue

    chunk_data = json.loads(chunk.get('bytes').decode())
    if chunk_data.get("type") == "content_block_delta":
      delta = chunk_data.get("delta", {})
      text = delta.get("text")
      if text:
        print(text, end='', flush=True)


def main():
  session = boto3.Session(profile_name="GSB570-BedrockOnly-490332585640")
  identity = session.client("sts").get_caller_identity()
  print("Account:", identity["Account"])
  print("UserId:", identity["UserId"])
  print("Arn:", identity["Arn"])

  print(call_bedrock_model("What is the captial of France?"))

  call_bedrock_model_with_streaming('\n\nHuman: what is the capital of the United States\n\nAssistant:')


if __name__ == "__main__":
  main()
