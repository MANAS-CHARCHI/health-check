from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# --- Extraction Schemas ---
class BillItem(BaseModel):
    description: str = Field(description="Name of the service or medicine")
    amount: float = Field(description="The cost of the item")

class ItemizedBillSchema(BaseModel):
    hospital_name: str
    items: List[BillItem]
    total_amount: float

class DischargeSchema(BaseModel):
    diagnosis: str
    admission_date: str
    discharge_date: str
    summary: str

class IDSchema(BaseModel):
    patient_name: str
    id_number: str
    dob: str

# --- Orchestration Schema ---
class DocClassification(BaseModel):
    id_pages: List[int] = Field(default_factory=list)
    bill_pages: List[int] = Field(default_factory=list)
    discharge_pages: List[int] = Field(default_factory=list)