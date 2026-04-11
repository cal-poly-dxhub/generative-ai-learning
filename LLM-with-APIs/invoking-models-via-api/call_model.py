import boto3
import json


def call_bedrock_model(message: str):
  client = boto3.client("bedrock-runtime", region_name="us-west-2")

  payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "messages": [{"role": "user", "content": message}],
  }

  response = client.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    body=json.dumps(payload)
  )

  response_body = json.loads(response["body"].read())
  return response_body["content"][0]["text"]


def call_bedrock_model_with_streaming(message: str):
  client = boto3.client("bedrock-runtime", region_name="us-west-2")

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
    modelId='anthropic.claude-3-5-haiku-20241022-v1:0',
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
  print(call_bedrock_model("What is the captial of France?"))

  call_bedrock_model_with_streaming('\n\nHuman: what is the capital of the United States\n\nAssistant:')


if __name__ == "__main__":
  main()

