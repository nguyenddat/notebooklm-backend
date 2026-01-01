from typing import *

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class SummarizeHistoryResponse(BaseModel):
    response: str = Field(..., description="Your summarized response based on the chat history.")

parser = PydanticOutputParser(pydantic_object=SummarizeHistoryResponse)