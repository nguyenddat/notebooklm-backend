from typing import Optional, List

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class SectionNodeResponse(BaseModel):
    index: int = Field(
        description="Index of the section or subsection in the document"
    )
    parent_index: Optional[int] = Field(
        description="Index of the parent section. None if this section is a top-level section"
    )


class CorrectSectionStructureResponse(BaseModel):
    response: List[SectionNodeResponse] = Field(
        description="List of section nodes representing the normalized hierarchical structure"
    )


parser = PydanticOutputParser(
    pydantic_object=CorrectSectionStructureResponse
)