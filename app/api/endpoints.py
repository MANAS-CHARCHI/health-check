from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from .. import models, database
from ..services.s3_services import S3Service
from ..services.textract import get_full_text
from ..services.graph_flow import app_graph
import uuid

router = APIRouter()
s3 = S3Service(bucket_name="my-claims-bucket")

async def run_extraction_pipeline(claim_id: str, process_id: str, db: Session):
    # 1. Get Text from Textract (OCR)
    record = db.query(models.ClaimRecord).filter_by(process_id=process_id).first()
    pages_text = await get_full_text(record.s3_input_pdf_key)
    
    # 2. Run LangGraph Orchestration
    final_state = await app_graph.ainvoke({
        "all_pages_text": pages_text,
        "classification": {},
        "extracted_results": {}
    })
    
    # 3. Store result in S3
    output_key = f"results/{claim_id}.json"
    s3.upload_json(final_state["extracted_results"], output_key)
    
    # 4. Update SQLite status
    record.status = "COMPLETED"
    record.s3_output_json_key = output_key
    db.commit()

@router.post("/process/{claim_id}")
async def process(claim_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    process_id = uuid.uuid4().hex
    s3_key = f"inputs/{claim_id}.pdf"
    
    # Upload to S3 and Create DB Log
    s3.upload_file(await file.read(), s3_key)
    new_record = models.ClaimRecord(claim_id=claim_id, process_id=process_id, s3_input_pdf_key=s3_key)
    db.add(new_record)
    db.commit()
    
    # Trigger background processing
    background_tasks.add_task(run_extraction_pipeline, claim_id, process_id, db)
    return {"process_id": process_id}

@router.get("/process/health/{claim_id}")
async def health_check(claim_id: str):
    return {"status": "online", "message": f"Claim Processing Service is running for claim {claim_id}"}