from fastapi import APIRouter
from schemas import QuestionRequest
from core.vector_store import search_documents

router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)

@router.post("/ask")
async def ask_question(request: QuestionRequest):

    results = search_documents(
        query=request.question,
        n_results=3
    )

    return {
        "status": "success",
        "question": request.question,
        "results": results
    }