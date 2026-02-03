import uuid
from typing import Optional, List

from pydantic import BaseModel, Field

class SectionNode(BaseModel):
    order_id: int = Field(..., description="Thứ tự của section trong source")
    
    label: Optional[str] = Field(None, description="Section label nếu có")
    title: Optional[str] = Field(None, description="Section title")
    content: str = Field("", description="Raw text content của section")
    
    parent_id: Optional[str] = Field(None, description="Parent section id")
    children: List["SectionNode"] = Field(default_factory=list)
    
    page: Optional[int] = Field(None, description="Trang của section nếu có")
    breadcrumb: Optional[str] = Field(None, description="Breadcrumb context của section")
    file_path: Optional[str] = Field(None, description="Đường dẫn tĩnh tới tài liệu gốc")
    filename: Optional[str] = Field(None, description="Tên file gốc")
    
    # Metadata cho image
    caption: Optional[str] = Field(None, description="Caption của ảnh")
    image_path: Optional[str] = Field(None, description="Đường dẫn image nếu section là image")
    
    def is_header(self) -> bool:
        return self.label == "header"
    
    def is_text(self) -> bool:
        return (not self.is_image()) and self.label != "header"
    
    def is_image(self) -> bool:
        return self.image_path is not None

    def is_leaf(self) -> bool:
        return len(self.children) == 0

SectionNode.model_rebuild()