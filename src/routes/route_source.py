import os
import uuid

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.encoders import jsonable_encoder

from core import config
from database import get_db
from models.entities import Source, User
from models.relationship import NotebookSource
from services import UserService, source_service, retrieve_service, notebook_source_service
from utils.hash import hash_file

router = APIRouter()

@router.get("/notebook/{notebook_id}/sources")
def get_sources_by_notebook_id(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(UserService.get_current_user),
):
    sources = source_service.get_sources_by_notebook_id(notebook_id, db)
    return [jsonable_encoder(source) for source in sources]

@router.post("/notebook/{notebook_id}/sources")
def create_source(
    notebook_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(UserService.get_current_user),
):
    file_hash = hash_file(file.file)
    existing_source = source_service.get_source_by_file_hash(file_hash, db)
    
    if existing_source:
        return existing_source

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(config.static_dir, unique_filename)
    
    source = Source(
        file_name=file.filename,
        file_hash=file_hash,
        file_path=file_path,
    )
    source_service.add(source, db)

    notebook_source = NotebookSource(notebook_id=notebook_id, source_id=source.id)
    notebook_source_service.add(notebook_source, db)

    retrieve_service.index_source(file_path, source.id, notebook_id)
    return jsonable_encoder(source)

@router.delete("/notebook/{notebook_id}/sources")
def delete_source(
    notebook_id: int,
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(UserService.get_current_user),
):
    notebook_source = db.query(NotebookSource).filter(
        NotebookSource.notebook_id == notebook_id,
        NotebookSource.source_id == source_id
    ).first()
    
    if notebook_source:
        db.delete(notebook_source)
        db.commit()
    
    source = source_service.get_by_id(source_id, db)
    if source:
        source_service.delete(source_id, db)
    
    # Xóa trong vectordb
    retrieve_service.delete_source(source_id, notebook_id)
    return {"status": "deleted"}