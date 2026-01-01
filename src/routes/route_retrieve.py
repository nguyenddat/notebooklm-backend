import os
import tempfile

from fastapi import APIRouter, File, Depends, UploadFile

from services import contextual_retrieval_service, retrieve_service

router = APIRouter()

@router.post("/contextual")
async def contextual_retrieval(
    user_query: str,
    file: UploadFile = File(...),
):
    # Tạo file tmp cho file    
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    md_text = contextual_retrieval_service.document_to_md(file_path=tmp_path)
    retriever = contextual_retrieval_service.build_faiss_index(md_text)
    return contextual_retrieval_service.query_relevant_documents(user_query, retriever, 5, 3)

from pydantic import BaseModel

class RetrieveRequest(BaseModel):
    user_query: str
    docs_ids: list[int] | None = None

@router.post("")
async def normal_retrieve(
    request: RetrieveRequest,
):
    documents = retrieve_service.retrieve(request.user_query, top_k=5, doc_ids=request.docs_ids)
    return documents
    