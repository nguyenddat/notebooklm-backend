from typing import *

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class RewriteQuestionResponse(BaseModel):
    rewritten_question: str = Field(..., description="Viết lại câu hỏi dựa trên lịch sử cuộc trò chuyện.")

parser = PydanticOutputParser(pydantic_object=RewriteQuestionResponse)