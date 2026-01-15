import uuid
from typing import Optional, List

from pydantic import BaseModel, Field

class SectionNode(BaseModel):
    point_id: str = Field(description="Unique id cho qdrant point",
                          default_factory=lambda: str(uuid.uuid4())
    )
    order_id: int = Field(..., description="Thứ tự của section trong source")
    
    label: Optional[str] = Field(None, description="Section label nếu có")
    title: Optional[str] = Field(None, description="Section title")
    content: str = Field("", description="Raw text content của section")
    
    breadcrumb: Optional[str] = Field(None, description="Breadcrumb context của section")
    parent_id: Optional[str] = Field(None, description="Parent section id")
    children: List["SectionNode"] = Field(default_factory=list)
    
    page: Optional[int] = Field(None, description="Trang của section nếu có")
    
    # Metadata cho image
    image_path: Optional[str] = Field(None, description="Đường dẫn image nếu section là image")
    
    
    def is_image(self) -> bool:
        return self.image_path is not None

    def is_leaf(self) -> bool:
        return len(self.children) == 0

SectionNode.model_rebuild()