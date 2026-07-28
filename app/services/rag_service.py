from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.services.chroma_service import retrieve_similar_cases
from app.schemas.incident_schemas import IncidentRequest, AnalysisResponse

# 1. Initialize Llama 3.2
llm = ChatOllama(model=settings.LLM_MODEL, temperature=0.2)

# 2. Traditional RAG Prompt Template
prompt = ChatPromptTemplate.from_template("""
You are an expert cybercrime and financial fraud analyst.
Analyze the user's incident using ONLY the historical complaint context provided below.

Context from previous cases:
{context}

User Incident Query:
{question}

Provide a structured response containing:
1. Threat Classification
2. Potential Legal/Regulatory Category
3. Actionable Mitigation Steps for the Victim
""")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def run_traditional_rag(request: IncidentRequest) -> AnalysisResponse:
    # 1. Retrieve matching cases from ChromaDB
    docs = retrieve_similar_cases(request.query, top_k=3)
    formatted_context = format_docs(docs)
    
    # 2. Build and invoke LCEL chain
    chain = prompt | llm | StrOutputParser()
    analysis_text = chain.invoke({
        "context": formatted_context,
        "question": request.query
    })
    
    # 3. Return structured API payload
    return AnalysisResponse(
        query=request.query,
        analysis=analysis_text,
        retrieved_context_count=len(docs)
    )