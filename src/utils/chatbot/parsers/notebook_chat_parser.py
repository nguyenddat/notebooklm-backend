from typing import *

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class NotebookChatResponse(BaseModel):
    response: str = Field(..., description="Your response based on the conversation history and retrieved documents.")
    recommendations: List[str] = Field(..., description="Suggested follow-up questions based on the user's query and provided documents.")
    citations: List[str] = Field(..., description="List of source citations referenced in the response.")

parser = PydanticOutputParser(pydantic_object=NotebookChatResponse)