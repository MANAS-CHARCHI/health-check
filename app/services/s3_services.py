import boto3
import json

class S3Service:
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name

    def upload_file(self, file_content, s3_key: str):
        self.s3.put_object(Bucket=self.bucket, Key=s3_key, Body=file_content)

    def get_json_data(self, s3_key: str):
        response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
        return json.loads(response['Body'].read().decode('utf-8'))