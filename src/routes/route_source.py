import os
import uuid

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.encoders import jsonable_encoder

from core import config
from database import get_db
from models.entities import Source, User
from models.relationship import NotebookSource
from services import UserService, source_service, notebook_source_service

router = APIRouter()

@router.get("/notebook/{notebook_id}/sources")
def get_sources_by_notebook_id(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(UserService.get_current_user),
):
    sources = source_service.get_sources_by_notebook_id(notebook_id, db)
    return [jsonable_encoder(source) for source in sources]