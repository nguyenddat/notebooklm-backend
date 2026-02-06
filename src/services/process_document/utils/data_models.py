from typing import List, Optional

from pydantic import BaseModel, Field

class DocImageModel(BaseModel):
    static_file_path: str = Field(description="đường dẫn static đến hình ảnh tài liệu")
    base64: str = Field(description="hình ảnh tài liệu dạng base64")
    mime_type: str = Field(description="loại mime của hình ảnh")

class DocPageModel(BaseModel):
    page_number: int = Field(description="số trang của tài liệu")
    base64: str = Field(None, description="hình ảnh trang tài liệu dạng base64")
    images: List[DocImageModel] = Field(description="danh sách hình ảnh trong trang tài liệu")
    mime_type: str = Field(description="loại mime của trang tài liệu")

class SectionNode(BaseModel):
    order_id: int = Field(..., description="Thứ tự của section trong source")
    
    label: Optional[str] = Field(None, description="Section label nếu có")
    content: str = Field("", description="Text content của section")
    
    parent_id: Optional[str] = Field(None, description="Parent section id")
    children: List["SectionNode"] = Field(default_factory=list)
    
    page: Optional[int] = Field(None, description="Trang của section nếu có")
    breadcrumb: Optional[str] = Field(None, description="Breadcrumb context của section")
    file_path: Optional[str] = Field(None, description="Đường dẫn tĩnh tới tài liệu gốc")
    filename: Optional[str] = Field(None, description="Tên file gốc")
    
    # Metadata cho image
    image_path: Optional[str] = Field(None, description="Đường dẫn image nếu section là image")
    
    def is_header(self) -> bool:
        return self.label == "header"
    
    def is_text(self) -> bool:
        return (not self.is_image()) and self.label != "header"
    
    def is_image(self) -> bool:
        return self.label == "image"

    def is_leaf(self) -> bool:
        return len(self.children) == 0

SectionNode.model_rebuild()