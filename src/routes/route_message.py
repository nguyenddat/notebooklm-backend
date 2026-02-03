import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.entities.model_message import MessageRole, Message
from services import message_service, UserService

router = APIRouter()

@router.get("/notebook/{notebook_id}/history")
def get_notebook_history(notebook_id: int, db: Session = Depends(get_db), current_user = Depends(UserService.get_current_user)):
    messages = message_service.get_last_messages_by_notebook_id(notebook_id, db)
    summary = message_service.summarize_conversation(messages)
    return {"summary": summary}

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

def format_retrieved_context(
    context: RetrievedContext,
    static_base_url: str = "static"
) -> str:
    sections: list[str] = []

    if context.texts:
        text_blocks = ["### Nội dung liên quan\n"]
        for idx, text in enumerate(context.texts, start=1):
            meta_lines = []
            meta_lines.append(f"**Tên gốc của file:** {text.filename} - Đường dẫn: {text.file_path}")
            if text.breadcrumb:
                meta_lines.append(f"**Mục:** {text.breadcrumb} - Trang: {text.page}")
            meta = "\n".join(meta_lines)
            text_blocks.append(
                f"({idx}) {meta}\n{text.strip()}"
            )
        sections.append("\n".join(text_blocks))

    if context.images:
        image_blocks = ["\n### Hình ảnh có thể liên quan minh họa\n"]

        for idx, img in enumerate(context.images, start=1):
            meta_lines = []

            meta_lines.append(f"**Tên gốc của file:** {img.filename}\nĐường dẫn: {img.file_path}")
            if img.breadcrumb:
                meta_lines.append(f"**Mục:** {img.breadcrumb} - Trang: {img.page}")

            meta = "\n".join(meta_lines)

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

    documents = json.dumps(
        message_request.documents.model_dump(),
        ensure_ascii=False,
        indent=2
    )
    # Tạo AI response dựa trên truy vấn, lịch sử và tài liệu được truy xuất
    ai_response = message_service.chat(
        query=message_request.query,
        history=message_request.history,
        documents=documents
    )
    
    print(ai_response)
    return ai_response