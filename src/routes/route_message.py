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

class RetrievedImage(BaseModel):
    caption: str
    image_path: str
    page: int | None = None
    breadcrumb: str | None = None

class RetrievedContext(BaseModel):
    texts: list[str] = []
    images: list[RetrievedImage] = []

class MessageCreateRequest(BaseModel):
    query: str
    history: str
    documents: RetrievedContext

def format_retrieved_context(
    context: RetrievedContext,
    static_base_url: str = "http://localhost:8000/static"
) -> str:
    sections: list[str] = []

    if context.texts:
        text_blocks = ["### Nội dung liên quan\n"]
        for idx, text in enumerate(context.texts, start=1):
            text_blocks.append(
                f"({idx}) {text.strip()}"
            )
        sections.append("\n\n".join(text_blocks))

    if context.images:
        image_blocks = ["\n### Hình ảnh có thể liên quan minh họa\n"]

        for idx, img in enumerate(context.images, start=1):
            meta_lines = []

            if img.breadcrumb:
                meta_lines.append(f"**Mục:** {img.breadcrumb}")

            if img.page is not None:
                meta_lines.append(f"**Trang:** {img.page}")

            meta = " · ".join(meta_lines)

            # Markdown image (static path)
            image_url = f"{static_base_url}/{img.image_path}"
            image_blocks.append(
                "\n".join(filter(None, [
                    f"({idx}) {meta}" if meta else f"({idx})",
                    f"![{img.caption}]({image_url})",
                    f"*{img.caption}*"
                ]))
            )

        sections.append("\n\n".join(image_blocks))

    return "\n\n".join(sections)

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

    print(format_retrieved_context(message_request.documents))
    # Tạo AI response dựa trên truy vấn, lịch sử và tài liệu được truy xuất
    ai_response = message_service.chat(
        query=message_request.query,
        history=message_request.history,
        documents=format_retrieved_context(message_request.documents))
        # documents=format_retrieved_texts(message_request.documents)

    ai_message = Message(
        notebook_id=notebook_id,
        role=MessageRole.ASSISTANT,
        content=json.dumps(ai_response)
    )
    message_service.add(ai_message, db)

    return ai_response