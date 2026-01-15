from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from database import get_db
# from services import retrieve_service
from models.entities import Source

router = APIRouter()

# from pydantic import BaseModel

# class RetrieveRequest(BaseModel):
#     user_query: str
#     source_id: int

# @router.post("")
# async def normal_retrieve(
#     request: RetrieveRequest,
#     db: Session = Depends(get_db),
# ):
#     source_id = request.source_id
#     source = db.query(Source).filter(Source.id == source_id).first()
#     if not source:
#         raise HTTPException(status_code=404, detail="Source not found")
    
#     hierarchical_tree = source.structure_config

#     documents = retrieve_service.retrieve(
#         request.user_query, 
#         top_k=5, 
#         source_id=request.source_id,
#         # hierarchical_tree=retrieve_service._dict_to_pydantic(hierarchical_tree)
#     )
#     return documents
    