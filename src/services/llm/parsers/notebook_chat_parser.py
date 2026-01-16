from typing import List, Literal, Union
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class TextMessage(BaseModel):
    type: Literal["text"] = "text"
    content: str = Field(..., description="Nội dung trả lời dạng văn bản thuần.")

class ImageMessage(BaseModel):
    type: Literal["image"] = "image"
    caption: str = Field(..., description="Mô tả hoặc chú thích của hình ảnh.")
    image_path: str = Field(..., description="Đường dẫn tĩnh tới hình ảnh.")

MessageItem = Union[TextMessage, ImageMessage]

class NotebookChatResponse(BaseModel):
    messages: List[MessageItem] = Field(
        ...,
        description="Danh sách message theo đúng thứ tự xuất hiện, gồm text và image."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Danh sách câu hỏi hoặc bước tiếp theo gợi ý."
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Danh sách nguồn trích dẫn trong tài liệu."
    )

parser = PydanticOutputParser(pydantic_object=NotebookChatResponse)