from enum import Enum
from typing import List

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class Label(str, Enum):
    HEADER = "header"
    TEXT = "text"
    
class DocSegmentResponse(BaseModel):
    index: int = Field(..., description="Vị trí đoạn trong tài liệu, bắt đầu từ 0")    
    label: Label = Field(..., description="Loại đoạn văn bản")
    content: str = Field(..., description="Nội dung đoạn, có thể là văn bản thuần túy hoặc caption của ảnh")

class OcrResponse(BaseModel):
    ocr_response: List[DocSegmentResponse] = Field(..., description="Danh sách các đoạn đã được phân loại và trích xuất nội dung")
    
parser = PydanticOutputParser(pydantic_object=OcrResponse)