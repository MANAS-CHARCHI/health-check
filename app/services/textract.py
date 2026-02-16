import boto3
import asyncio
from typing import List

# Configure your AWS region
REGION = "us-east-1"
textract = boto3.client("textract", region_name=REGION)

async def get_full_text(s3_key: str, bucket_name: str = "my-claims-bucket") -> List[str]:
    """
    Triggers Textract, polls for completion, and returns a list where 
    each element is the full text of a single page.
    """
    # 1. Start the Asynchronous Job
    # We use StartDocumentAnalysis to support Tables/Forms in the future
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

    # 2. Poll for Completion
    # We loop every 2 seconds to check if AWS is finished
    while True:
        status_resp = textract.get_document_analysis(JobId=job_id)
        status = status_resp["JobStatus"]
        
        if status == "SUCCEEDED":
            break
        elif status == "FAILED":
            raise Exception(f"Textract job {job_id} failed.")
        
        await asyncio.sleep(2)

    # 3. Retrieve All Results (Handling Pagination)
    # AWS returns results in chunks of 1000 blocks. We must use NextToken
    # to "stitch" the full document together.
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