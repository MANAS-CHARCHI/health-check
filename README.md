# health-check
![alt text](image-1.png)
# Medical Claim Intelligence System (FastAPI & LangGraph)

## Used TechStack & Tools
1. FastAPI + SQLAlchemy + uv
2. LangGraph
3. Sqlite
4. AWS S3
5. Amazon Textract(async method)
6. Amazon Bedrock (amazon.nova-pro-v1:0 model) 

# Technical WorkFlow
1. When Backend get the file and claim_id it store the file in s3 and in database a new record is created with the claim_id and s3 file path with the status: STARTED
2. After that a Background process will start which first invoke Amazon textract to get the text from the pdf. **FYI:Amazon Textract is a ML based OCR.**
3. Backend do a short polling (call every 2 sec) to textract for the responce, once textract have the responce, it start getting the responce in a sequence.
4. Then With **LangGraph** make the Segregator as the root node which  start the Segregation by calling the model with 2000 character from everypage to know which page have which type of data and get required page numbers for id, bill and discharge page.
5. Then it created 3 nodes calling Id_agent, bill_agent and discharge_agent in parallal. send the appropriate call to the llm with type safety with **Pydentic** schemas.
6. Get the Responce and then currect the order that Identification will be in the top, then medical_summery and then billing. Make a list outof it
7. Store the data in S3 and also save the path in the database with status **Completed**.
8. User then need to call the Claim **GET** endpoint to get the responce. If it say its under processing user shoudl try after a second or two.
9. If User try uploading another document with the same claim_id it will show the claim is processed even if the file is different.


## How it Works
1. **OCR Layer**: Uses AWS Textract to extract raw text and table data asynchronously.
2. **Segregator Agent**: Analyzes page previews to route specific pages to specialist agents.
3. **Specialist Agents**: ID, Billing, and Clinical agents run in **parallel** to extract structured data using Amazon Bedrock LLMs .
4. **Validation**: Pydantic schemas enforce data integrity before saving the final results to S3.

---

## Work Flow
1. User Upload the file with the claim_id. (File has to be PDF for now)
2. After Upload the file and once backend get the correct file, if the claim is unique a background process will start as soon as user uplaod the file.
3. after a few sec user get the detailed result, if the process is complete user get the responce in proper format, or if the process is not completed user should try again after a few second.


## Prep your environment
We use `uv` because it's significantly faster for dependency management.

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync

# Add there in .env file
S3_BUCKET_NAME=medical-doc-analysis
S3_REGION_NAME=us-east-1
S3_BUCKET_NAME_FOR_PDFS=my_claims_raw_pdfs
S3_OUTPUT_BUCKET_NAME=my-claims-processed
CLASSIFICATION_MODEL_ID=amazon.nova-pro-v1:0

# Run the backend
uv run uvicorn app.main:app --reload