from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.schemas.incident_schemas import IncidentRequest, AnalysisResponse
from app.services.rag_service import run_traditional_rag
from app.services.ocr_service import extract_text_from_image

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_incident(
    query: str = Form(None, description="The user's text complaint"),
    file: UploadFile = File(None, description="Screenshot of the scam/fraud")
):
    try:
        if not query and not file:
            raise HTTPException(
                status_code=400, 
                detail="Must provide either a text 'query' or an image 'file'."
            )
            
        combined_text = ""
        
        # 1. Process Text Query
        if query:
            combined_text += query.strip() + "\n"
            
        # 2. Process Image OCR
        if file:
            print(f"[analyze] Processing image: {file.filename}")
            image_bytes = await file.read()
            ocr_text = extract_text_from_image(image_bytes)
            combined_text += f"\n[Extracted from Image]: {ocr_text}"
            
        print(f"[analyze] Final Query sent to RAG:\n{combined_text}")
        
        # 3. Create request object & execute pipeline
        request = IncidentRequest(query=combined_text.strip())
        response = run_traditional_rag(request)
        
        return response

    except HTTPException:
        # Preserve intentional client errors (e.g. the 400 above) as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))