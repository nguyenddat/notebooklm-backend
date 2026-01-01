import os
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.encoders import jsonable_encoder

from core import config
from database import get_db
from models.entities import User, Notebook, Source
from models.relationship import NotebookSource
from services import UserService, notebook_service, source_service, retrieve_service, notebook_source_service
from utils.hash import hash_file

router = APIRouter()
    
@router.get("")
def get_notebooks(
    limit: int=20,
    last_id: Optional[int]=0,
    db: Session = Depends(get_db),
    current_user: User = Depends(UserService.get_current_user)
):
    notebooks = notebook_service.get_notebooks_by_user_id_paginated(current_user.id, db, limit, last_id)
    return [jsonable_encoder(notebook) for notebook in notebooks]

@router.post("")
def create_notebook(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db), 
    current_user: User = Depends(UserService.get_current_user)
):
    failed_files = []
    valid_files = []
    
    # Nếu không có file nào hợp lệ: pdf, docx, image thì báo lỗi
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
    ]
    for file in files:
        if file.content_type not in allowed_types:
            failed_files.append({"filename": file.filename, "error": "Invalid file type"})
        else:
            valid_files.append(file)
    
    if not valid_files:
        raise HTTPException(status_code=400, detail="No valid files uploaded")
    
    # Tạo notebook
    new_notebook = Notebook(title=valid_files[0].filename, user_id=current_user.id)
    new_notebook = notebook_service.add(new_notebook, db)
    
    # Lưu vào static dir -> Lưu vào vectordb -> Tạo source
    success_file = []
    for file in valid_files:
        file_hash = hash_file(file.file)
        file_name = file.filename
        
        existed_source = source_service.get_source_by_file_hash(file_hash, db)
        if existed_source:
            source = existed_source
        else:
            unique_filename = str(uuid.uuid4())
            file_extension = os.path.splitext(file.filename)[1]
            file_path = os.path.join(config.static_dir, unique_filename + file_extension)

            with open(file_path, "wb") as f:
                f.write(file.file.read())

            source = Source(
                title=file_name,
                filename=file_name,
                file_path=file_path,
                file_hash=file_hash,
            )
            source = source_service.add(source, db)

            notebook_source = NotebookSource(notebook_id=new_notebook.id, source_id=source.id)
            notebook_source_service.add(notebook_source, db)

            retrieve_service.index_source(source.id, file_path, new_notebook.id)

        success_file.append(source)        
    
    return {
        "notebook": jsonable_encoder(new_notebook),
        "success_files": [jsonable_encoder(source) for source in success_file],
        "failed_files": failed_files, 
    }
    
@router.delete("")
def delete_notebook(
    notebook_id: int,
    db: Session = Depends(get_db), 
    current_user: User = Depends(UserService.get_current_user)
):
    notebook_service.delete(notebook_id, db)
    return {"status": "deleted"}