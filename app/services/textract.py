import boto3
import asyncio
from typing import List
from dotenv import load_dotenv
import os
load_dotenv()

REGION = os.getenv("S3_REGION_NAME")
textract = boto3.client("textract", region_name="us-east-1")


async def get_full_text(s3_key: str, bucket_name: str = os.getenv("S3_BUCKET_NAME")) -> List[str]:
    """
    Triggers Textract, polls for completion, and returns a list where each element is the full text.
    """
    s3_test = boto3.client("s3", region_name=REGION)
    s3_key = s3_key.lstrip('/')
    print(f"DEBUG: Attempting to find Bucket: {bucket_name} | Key: {s3_key} | Region: {REGION}")
    try:
        meta = s3_test.head_object(Bucket=bucket_name, Key=s3_key)
        print(f"✅ S3 SUCCESS: File size is {meta['ContentLength']} bytes")
    except Exception as e:
        print(f"❌ S3 ERROR: {str(e)}")
        # This will tell you if it's '404 Not Found' or '403 Forbidden'
        raise e
    response = textract.start_document_analysis(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': s3_key
            }
        },
        FeatureTypes=['TABLES', 'FORMS'] 
    )
    job_id = response["JobId"]

    # Loop every 2 seconds to check if AWS is finished
    while True:
        status_resp = textract.get_document_analysis(JobId=job_id)
        status = status_resp["JobStatus"]
        
        if status == "SUCCEEDED":
            break
        elif status == "FAILED":
            raise Exception(f"Textract job {job_id} failed.")
        
        await asyncio.sleep(2)

    # AWS returns results in chunks of 1000 blocks. We must use NextToken
    pages_map = {}
    next_token = None
    
    while True:
        kwargs = {"JobId": job_id}
        if next_token:
            kwargs["NextToken"] = next_token
        
        result_page = textract.get_document_analysis(**kwargs)
        
        # Process Blocks
        for block in result_page.get("Blocks", []):
            if block["BlockType"] == "LINE":
                page_num = block.get("Page", 1) - 1 # 0-indexed
                text = block.get("Text", "")
                
                if page_num not in pages_map:
                    pages_map[page_num] = ""
                pages_map[page_num] += text + " "

        next_token = result_page.get("NextToken")
        if not next_token:
            break

    # Sort by page number and return as a list of strings
    return [pages_map[i] for i in sorted(pages_map.keys())]