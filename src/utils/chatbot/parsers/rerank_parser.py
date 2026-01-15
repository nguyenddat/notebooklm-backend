from typing import *

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class RerankResponse(BaseModel):
    reranked_indices: List[int] = Field(..., description="List of document indices sorted by relevance to the query.")

parser = PydanticOutputParser(pydantic_object=RerankResponse)