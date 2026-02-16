import uvicorn
from fastapi import FastAPI
from .database import engine, Base
from .api import endpoints
from .models import ClaimRecord  # Ensure models are imported to register with Base

# 1. Initialize Database Tables
# This command tells SQLAlchemy to create the 'claims' table in claims.db 
# if it doesn't already exist.
Base.metadata.create_all(bind=engine)

# 2. Initialize FastAPI App
app = FastAPI(
    title="Medical Claim Processor",
    description="Modular system for processing medical claims using LangGraph and AWS",
    version="1.0.0"
)

# 3. Include API Routers
# We keep the code modular by moving route logic to app/api/endpoints.py.
app.include_router(endpoints.router, prefix="/api", tags=["Claims"])

# 4. Root Health Check
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "online", "message": "Claim Processing Service is running"}

if __name__ == "__main__":
    # To run locally using 'uv run python app/main.py'
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)