from sqlalchemy import Column, String, DateTime
from datetime import datetime
from .database import Base

class ClaimRecord(Base):
    __tablename__ = "claims"

    claim_id = Column(String, primary_key=True, index=True)
    process_id = Column(String, unique=True, index=True)
    status = Column(String, default="PROCESSING")  # PROCESSING, COMPLETED, FAILED
    
    # S3 paths instead of storing data in DB
    s3_input_pdf_key = Column(String)   # e.g., "raw/claim_123.pdf"
    s3_output_json_key = Column(String) # e.g., "results/claim_123.json"
    
    created_at = Column(DateTime, default=datetime.utcnow)