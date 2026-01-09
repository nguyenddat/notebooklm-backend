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
from utils import hash_file, check_valid_file_type

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

@router.get("/{notebook_id}")
def get_notebook_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(UserService.get_current_user)
):
    notebook = notebook_service.get_by_id(id, db)
    return jsonable_encoder(notebook)

@router.post("")
def create_notebook(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db), 
    current_user: User = Depends(UserService.get_current_user)
):    
    # Nếu không có file nào hợp lệ: pdf, docx, image thì báo lỗi
    valid_files = []
    failed_files = []
    for file in files:
        if check_valid_file_type(file.content_type):
            valid_files.append(file)
        else:
            failed_files.append(file)
    
    # Tạo notebook
    new_notebook = Notebook(title=valid_files[0].filename, user_id=current_user.id)
    new_notebook = notebook_service.add(new_notebook, db)
    
    # Xử lý các file hợp lệ
    success_file = []
    for file in valid_files:
        file_hash = hash_file(file.file)
        file_name = file.filename
        
        existed_source = source_service.get_source_by_file_hash(file_hash, db)
        if existed_source:
            source = existed_source
            success_file.append(source)
            continue

        unique_filename = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        file_path = os.path.join(config.static_dir, unique_filename + file_extension)
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        # Process thành công mới lưu vào db
        
        source = Source(
            title=file_name,
            filename=file_name,
            file_path=file_path,
            file_hash=file_hash,
        )
        source = source_service.add(source, db)

        notebook_source = NotebookSource(notebook_id=new_notebook.id, source_id=source.id)
        notebook_source_service.add(notebook_source, db)

        tree = retrieve_service.process_file(source.id, file_path, new_notebook.id)
        retrieve_service.index(source.id, tree, new_notebook.id)
        
        tree = retrieve_service._pydantic_to_dict(tree)
        source.structure_config = tree
        db.commit()
        db.refresh(source)
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