from pydantic import BaseModel, Field

class IncidentRequest(BaseModel):
    query: str = Field(
        ..., 
        example="Victim reported unauthorized charges on credit card and the bank refused to investigate."
    )

class AnalysisResponse(BaseModel):
    query: str
    analysis: str
    retrieved_context_count: int