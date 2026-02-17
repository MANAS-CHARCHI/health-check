import boto3
import json

class S3Service:
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name

    def upload_file(self, file_content, s3_key: str):
        self.s3.put_object(Bucket=self.bucket, Key=s3_key, Body=file_content)

    def upload_json(self, data: dict, s3_key: str):
        """Converts dict to JSON string and uploads to S3"""
        json_content = json.dumps(data)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=json_content,
            ContentType='application/json'
        )

    def wait_for_object(self, s3_key: str):
        waiter = self.s3.get_waiter('object_exists')
        waiter.wait(
            Bucket=self.bucket,
            Key=s3_key,
            WaiterConfig={'Delay': 1, 'MaxAttempts': 5}
        )

    def get_json_data(self, s3_key: str):
        response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
        return json.loads(response['Body'].read().decode('utf-8'))