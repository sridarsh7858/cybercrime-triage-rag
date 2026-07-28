from fastapi import FastAPI, File, Form, UploadFile, HTTPException
import shutil
import os

# Import the OCR engine from your services folder
from app.services.ocr_service import ocr_engine

app = FastAPI(
    title="Multimodal Threat Intelligence API",
    description="Local backend for cybercrime text and screenshot triage."
)

UPLOAD_DIR = os.path.join("data", "temp_evidence")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def health_check():
    return {"status": "System Online", "environment": "Local Prototype"}

@app.post("/api/submit_complaint")
async def submit_complaint(
    complaint_text: str = Form(...), 
    evidence_image: UploadFile = File(...)
):
    if not evidence_image.filename:
        raise HTTPException(status_code=400, detail="No evidence file attached.")
        
    file_path = os.path.join(UPLOAD_DIR, evidence_image.filename)
    
    try:
        # 1. Save the file to disk so EasyOCR can locate it
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(evidence_image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write image file: {str(e)}")
        
    try:
        # 2. Extract text from the saved image payload using EasyOCR
        extracted_ocr_text = ocr_engine.extract_text_from_image(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR Extraction Engine failure: {str(e)}")
        
    # 3. Formulate Option B: Combine both strings in-memory for the RAG engine next
    unified_text_payload = f"Citizen Narrative: {complaint_text}\nExtracted Screenshot Evidence: {extracted_ocr_text}"
        
    return {
        "status": "Payload successfully received and extracted",
        "data": {
            "citizen_narrative": complaint_text,
            "extracted_evidence_text": extracted_ocr_text,
            "unified_text_length": len(unified_text_payload)
        },
        "meta": {
            "saved_image_location": file_path
        }
    }