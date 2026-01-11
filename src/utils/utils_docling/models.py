from typing import Optional, List, Union
from pydantic import BaseModel, Field

class TextLeaf(BaseModel):
    index: int = 0
    text: Optional[str]
    page: int

class ImageLeaf(TextLeaf):
    image_path: str

class SectionNode(BaseModel):
    index: int = 0
    title: str
    level: int
    start_page: Optional[int]
    end_page: Optional[int]
    children: List[Union["SectionNode", TextLeaf, ImageLeaf]] = []

SectionNode.model_rebuild()