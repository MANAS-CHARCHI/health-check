import uvicorn
from fastapi import FastAPI
from .database import engine, Base
from .api import endpoints
from .models import ClaimRecord

# Initialize DB Tables
Base.metadata.create_all(bind=engine)

# Initialize App
app = FastAPI(
    title="Medical Claim Processor",
    description="Modular system for processing medical claims.",
    version="1.0.0"
)

# Routing
app.include_router(endpoints.router, prefix="/api", tags=["Claims"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)