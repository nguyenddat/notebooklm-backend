from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core import logger
from database import get_db
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
        texts = [
            {
                "content": texts[i]["content"],
                "page": texts[i]["metadata"]["page_start"],
                "file_path": texts[i]["metadata"]["file_path"],
                "filename": texts[i]["metadata"]["filename"],
                "breadcrumb": " > ".join(texts[i]["metadata"]["breadcrumb"])
            }
            for i in doc_indices
        ]
    
    images = qdrant_service.search(
        query=question,
        source_ids=source_ids,
        type="image"
    )
    logger.info(
        f"Image retrieved include:\n"
        + "\n".join(f"- {image['content']}" for image in images)
    )

    return_images = []
    if images:
        params["num_docs"] = len(images)
        params["top_k"] = min(len(images), 3)
        params["documents"] = images
        doc_indices = llm_service.get_chat_completion(task, params)["reranked_indices"]
        for i in doc_indices:
            image = images[i]

            logger.info(
                f"Image retrieved after rerank include:\n"
                + "\n".join(f"- {image['content']}" for image in images)
            )
            return_images.append({
                "caption": image["content"],
                "image_path": image["metadata"].get("image_path"),
                "file_path": image["metadata"]["file_path"],
                "filename": image["metadata"]["filename"],
                "page": image["metadata"]["page_start"],
                "breadcrumb": " > ".join(image["metadata"]["breadcrumb"])
            })

    return {
        "texts": texts,
        "images": return_images
    }