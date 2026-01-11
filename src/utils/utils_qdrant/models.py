from pydantic import BaseModel
from typing import Optional, Literal

class QdrantPayload(BaseModel):
    source_id: str
    notebook_id: Optional[int]
    index: int
    type: Literal["text", "image"]
    text: str

    # image-only
    image_path: Optional[str] = None
    page: Optional[int] = None
    breadcrumb: Optional[str] = None
    

class IndexedChunk(BaseModel):
    chunk_id: str
    source_id: str
    notebook_id: Optional[int]
    text: str
    index: int
    type: Literal["text", "image"]
    embedding: list[float]

    # image
    image_path: Optional[str] = None
    page: Optional[int] = None
    breadcrumb: Optional[str] = None
    
class SearchResult(BaseModel):
    chunk_id: str
    score: float
    source_id: str
    type: Literal["text", "image"]
    text: str

    image_path: Optional[str] = None
    page: Optional[int] = None
    breadcrumb: Optional[str] = None