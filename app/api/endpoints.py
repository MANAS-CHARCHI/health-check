from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from .. import models, database
from ..services.s3_services import S3Service
from ..services.textract import get_full_text
from ..services.graph_flow import app_graph
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
s3 = S3Service(bucket_name=os.getenv("S3_BUCKET_NAME"))

async def run_extraction_pipeline(claim_id: str, db: Session):
    # Get Text from Textract
    record = db.query(models.ClaimRecord).filter_by(claim_id=claim_id).first()
    pages_text = await get_full_text(record.s3_input_pdf_key)
    
    # Run LangGraph
    final_state = await app_graph.ainvoke({
        "all_pages_text": pages_text,
        "classification": {},
        "extracted_results": {}
    })
    
    # Store result in S3
    output_key = f"processed/{claim_id}.json"
    s3.upload_json(final_state["extracted_results"], output_key)
    
    # Update SQLite status
    record.status = "COMPLETED"
    record.s3_output_json_key = output_key
    db.commit()

from fastapi import HTTPException, status
@router.post("/process/{claim_id}")
async def process(claim_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    existing_record = db.query(models.ClaimRecord).filter_by(claim_id=claim_id).first()
    if existing_record:
        # If it exists and is already completed, tell them to check the health endpoint
        if existing_record.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ALREADY_PROCESSED",
                    "message": f"Claim {claim_id} has already been processed.",
                    "action": f"Please check the results at /check/health/{claim_id}"
                }
            )
        # If it exists but is still pending, tell them to wait
        else:
            return {
                "status": existing_record.status,
                "message": f"Claim {claim_id} is currently being processed. Please wait."
            }
    # Upload to S3 and Create DB Log
    s3_key = f"raw_pdfs/{claim_id}.pdf"

    try:
        content = await file.read()
        s3.upload_file(content, s3_key)
        new_record = models.ClaimRecord(
            claim_id=claim_id, 
            s3_input_pdf_key=s3_key,
            status="PENDING"
        )
        db.add(new_record)
        db.commit()
        background_tasks.add_task(run_extraction_pipeline, claim_id, db)
        return {"message": "File uploaded and processing started, Please check after a few seconds.", "claim_id": claim_id, "status": "STARTED"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/check/health/{claim_id}")
async def health_check(claim_id: str, db: Session = Depends(database.get_db)):
    # Look up the record by the unique claim_id
    record = db.query(models.ClaimRecord).filter_by(claim_id=claim_id).first()

    if not record:
        return {"status": "NOT_FOUND", "message": "Invalid Claim ID"}

    if record.status == "PENDING":
        return {"status": "PROCESSING", "message": "Extraction in progress..."}

    if record.status == "COMPLETED":
        # Fetch the final JSON from S3 so the client gets the data immediately
        try:
            result_json = s3.get_json_data(record.s3_output_json_key)
            return {
                "status": "COMPLETED",
                "claim_id": record.claim_id,
                "result": result_json
            }
        except Exception as e:
            return {"status": "ERROR", "message": "Result found but failed to load from S3"}

    return {"status": "FAILED", "message": "Something went wrong during processing"}

