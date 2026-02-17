#!/bin/sh
# Setup AWS credentials on the fly
mkdir -p ~/.aws
echo "[default]
aws_access_key_id = ${AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY}" > ~/.aws/credentials

echo "[default]
region = ${AWS_DEFAULT_REGION}
output = json" > ~/.aws/config

# Run the main command
exec "$@"