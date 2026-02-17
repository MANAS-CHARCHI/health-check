from sqlalchemy import Column, String, DateTime
from datetime import datetime
from .database import Base

class ClaimRecord(Base):
    __tablename__ = "claims"

    claim_id = Column(String, primary_key=True, index=True)
    status = Column(String, default="PROCESSING")  # STARTED, PROCESSING, COMPLETED, FAILED
    
    # S3 paths
    s3_input_pdf_key = Column(String)
    s3_output_json_key = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)