import uuid
from typing import Literal, List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field, ConfigDict

class QdrantDocumentMetadata(BaseModel):
    file_path: str = Field(..., description="Đường dẫn tĩnh tới tài liệu gốc")
    filename: str = Field(..., description="Tên file gốc")
    page_start: int = Field(..., description="Trang bắt đầu của nội dung")
    page_end: int = Field(..., description="Trang kết thúc của nội dung")
    breadcrumb: List[str] = Field(
        default_factory=list, 
        description="Đường dẫn phân cấp của tài liệu (ví dụ: Chương > Mục > Tiểu mục)"
    )
    
    image_path: Optional[str] = None
    image_caption: Optional[str] = Field(None, description="Mô tả nếu type là image")


class QdrantBaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID của point trong Qdrant"
    )

    content: str = Field(
        ..., description="Nội dung của point"
    )
    
    type: Literal["text", "image"] = Field(
        ..., description="Loại document: text hoặc image"
    )

    source_id: Optional[int] = Field(
        None, description="ID của source (tài liệu gốc)"
    )
    
    metadata: QdrantDocumentMetadata = Field(
        ..., description="Thông tin chi tiết đi kèm"
    )