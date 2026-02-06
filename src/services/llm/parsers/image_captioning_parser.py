from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class ImageCaptionResponse(BaseModel):
    description: str = Field(...,description="Mô tả ngắn gọn về nội dung chính của hình ảnh.")

parser = PydanticOutputParser(pydantic_object=ImageCaptionResponse)