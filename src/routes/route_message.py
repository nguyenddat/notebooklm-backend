import os
import json
import base64
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import config
from database import get_db
from models.entities.model_message import MessageRole, Message
from services import message_service, notebook_service, UserService, llm_service

router = APIRouter()

@router.get("/notebook/{notebook_id}/messages")
def get_notebook_messages(
    notebook_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(UserService.get_current_user)
):
    messages = message_service.get_messages_by_notebook_id(notebook_id, db)
    return {
        "messages": [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": json.loads(msg.content) if msg.role.value == "assistant" else msg.content,
                "citations": json.loads(msg.citations) if msg.citations else [],
                "summary": msg.summary,
                "created_at": msg.created_at
            }
            for msg in messages
        ]
    }

@router.get("/notebook/{notebook_id}/rewrite")
def rewrite_question(
    question: str,
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(UserService.get_current_user)
):
    # Lấy 3 tin nhắn gần nhất
    history = message_service.get_last_messages_by_notebook_id(notebook_id, db)[:3]

    # Các tin nhắn từ assistant sẽ lấy summary làm content
    formatted_history = ""
    for msg in history:
        if msg.role == MessageRole.ASSISTANT:
            formatted_history += f"Assistant: {msg.summary}\n"
        else:
            formatted_history += f"User: {msg.content}\n"
    
    # Gọi llm để tóm tắt
    params = {
        "question": question,
        "conversation_history": formatted_history,
    }
    result = llm_service.get_chat_completion("rewrite_question", params)
    return result

from pydantic import BaseModel

class RetrievedImage(BaseModel):
    caption: str
    
    filename: str
    file_path: str
    image_path: str
    
    page: int | None = None
    breadcrumb: str | None = None

class RetrievedText(BaseModel):
    content: str
    filename: str
    file_path: str
    page: int | None = None
    breadcrumb: str | None = None

class RetrievedContext(BaseModel):
    texts: list[RetrievedText] = []
    images: list[RetrievedImage] = []

class MessageCreateRequest(BaseModel):
    query: str
    history: str
    documents: RetrievedContext

def format_retrieved_context(context: RetrievedContext) -> str:
    sections: list[str] = []
    if context.texts:
        text_blocks = ["### Nội dung liên quan\n"]
        for idx, text in enumerate(context.texts, start=1):
            meta_lines = []
            meta_lines.append(f"**Tên gốc của file:** {text.filename} - Đường dẫn: {text.file_path.replace('\\', '/').replace('app/static/', '')}")
            if text.breadcrumb:
                meta_lines.append(f"**Mục:** {text.breadcrumb} - Trang: {text.page}")
            meta = "\n".join(meta_lines)
            text_blocks.append(
                f"({idx}) {meta}\n{text.content.strip()}"
            )
        sections.append("\n".join(text_blocks))

    if context.images:
        image_blocks = ["\n### Hình ảnh có thể liên quan minh họa\n"]

        for idx, img in enumerate(context.images, start=1):
            meta_lines = []
            meta_lines.append(f"**Tên gốc của file:** {img.filename}\nĐường dẫn: {img.file_path.replace('\\', '/').replace('app/static/', '')}")
            if img.breadcrumb:
                meta_lines.append(f"**Mục:** {img.breadcrumb} - Trang: {img.page}")

            meta = "\n".join(meta_lines)

            # Markdown image (static path)
            image_url = f"{img.image_path}"
            image_blocks.append(
                "\n".join(filter(None, [
                    f"({idx}) {meta}" if meta else f"({idx})",
                    f"![{img.caption}]({image_url})",
                    f"*{img.caption}*"
                ]))
            )

        sections.append("\n".join(image_blocks))

    return "\n".join(sections)

def image_path_to_base64(image_path: str) -> str:
    clean_path = image_path.lstrip("/")
    path = os.path.join(config.static_dir, clean_path)
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return encoded

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
    
    ai_response = message_service.chat(
        query=message_request.query,
        documents=format_retrieved_context(message_request.documents)
    )
    
    # Convert messages and citations to JSON string for storage
    messages_content = json.dumps(ai_response.get("messages", []))
    citations_content = json.dumps(ai_response.get("citations", []))
    summary = ai_response.get("summary", "")
    
    # Save AI message to database
    ai_message = Message(
        notebook_id=notebook_id,
        role=MessageRole.ASSISTANT,
        content=messages_content,
        citations=citations_content,
        summary=summary
    )
    message_service.add(ai_message, db)
    
    # Update notebook title with the latest summary
    if summary:
        notebook = notebook_service.get_by_id(notebook_id, db)
        if notebook:
            notebook.title = summary
            db.commit()
    
    return ai_response