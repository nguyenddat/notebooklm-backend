from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from database import get_db
from models.entities import Source
from services import qdrant_service, llm_service

router = APIRouter()

from typing import List
from pydantic import BaseModel

class RetrieveRequest(BaseModel):
    user_query: str
    source_ids: List[int]

@router.post("")
async def normal_retrieve(
    request: RetrieveRequest,
    db: Session = Depends(get_db),
):
    question = request.user_query
    source_ids = request.source_ids

    task = "rerank" 
    params = {"question": question}
    # Query -> rerank
    texts = qdrant_service.search(
        query=question,
        source_ids=source_ids,
        type="text"
    )
    if texts:
        params["num_docs"] = len(texts)
        params["top_k"] = min(len(texts), 3)
        params["documents"] = texts
        doc_indices = llm_service.get_chat_completion(task, params)["reranked_indices"]
        texts = [texts[i]["content"] for i in doc_indices if isinstance(i, int) and 0 <= i < len(texts)]
    
    images = qdrant_service.search(
        query=question,
        source_ids=source_ids,
        type="image"
    )
    return_images = []
    if images:
        params["num_docs"] = len(images)
        params["top_k"] = min(len(images), 3)
        params["documents"] = images
        doc_indices = llm_service.get_chat_completion(task, params)["reranked_indices"]
        for i in doc_indices:
            image = images[i]
            return_images.append({
                "caption": image["content"],
                "image_path": image["metadata"].get("image_path"),
                "page": image["metadata"]["page_start"],
                "breadcrumb": " > ".join(image["metadata"]["breadcrumb"])
            })

    return {
        "texts": texts,
        "images": return_images
    }