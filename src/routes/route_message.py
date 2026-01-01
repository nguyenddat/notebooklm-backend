import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.entities.model_message import MessageRole, Message
from services import message_service, retrieve_service, UserService

router = APIRouter()

@router.get("/notebook/{notebook_id}/history")
def get_notebook_history(notebook_id: int, db: Session = Depends(get_db), current_user = Depends(UserService.get_current_user)):
    messages = message_service.get_last_messages_by_notebook_id(notebook_id, db)
    summary = message_service.summarize_conversation(messages)
    return {"summary": summary}

from pydantic import BaseModel

class DocumentRetrieved(BaseModel):
    chunk_id: int
    score: float
    text: str
    doc_id: int
    page: int

class MessageCreateRequest(BaseModel):
    query: str
    history: str
    documents: list[DocumentRetrieved]

def format_retrieved_texts(documents: list[DocumentRetrieved]) -> str:
    formatted_texts = []
    for doc in documents:
        formatted_texts.append(f"[DocID: {doc.doc_id} | Page: {doc.page}]\n{doc.text.strip()}\n")
    return "\n".join(formatted_texts)

@router.post("/notebook/{notebook_id}/message")
def post_notebook_message(
    notebook_id: int,
    message_request: MessageCreateRequest,
    db = Depends(get_db),
    current_user = Depends(UserService.get_current_user)
):
    user_message = Message(
        notebook_id=notebook_id,
        role=MessageRole.USER,
        content=message_request.query
    )
    message_service.add(user_message, db)

    # Tạo AI response dựa trên truy vấn, lịch sử và tài liệu được truy xuất
    ai_response = message_service.chat(
        query=message_request.query,
        history=message_request.history,
        documents=format_retrieved_texts(message_request.documents)
    )

    ai_message = Message(
        notebook_id=notebook_id,
        role=MessageRole.AI,
        content=json.dumps(ai_response)
    )
    message_service.add(ai_message, db)

    return ai_response