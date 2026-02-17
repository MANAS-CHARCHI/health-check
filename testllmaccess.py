import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

# The correct body structure for Amazon Nova
body_content = {
    "inferenceConfig": {
        "max_new_tokens": 100,
        "temperature": 0.7
    },
    "messages": [
        {
            "role": "user",
            "content": [
                {"text": "Explain AI in one sentence."}
            ]
        }
    ]
}

response = client.invoke_model(
    modelId="amazon.nova-pro-v1:0",
    body=json.dumps(body_content)
)

# Parsing the specific Nova response structure
result = json.loads(response["body"].read())
print(result["output"]["message"]["content"][0]["text"])