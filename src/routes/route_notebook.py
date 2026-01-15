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
from services.source.srv_docling import docling_service
from services import UserService, notebook_service, source_service, notebook_source_service
from utils import get_bytes_and_hash, check_valid_file_type

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
    # Query notebook
    notebook = notebook_service.get_by_id(id, db)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook không tồn tại.")
    
    if notebook.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập notebook này.")
    
    sources = source_service.get_sources_by_notebook_id(notebook.id, db)

    result = jsonable_encoder(notebook)
    result["sources"] = [jsonable_encoder(source) for source in sources]    
    return result

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
    
    if not valid_files:
        raise HTTPException(400, detail="Không file nào hợp lệ với định dạng hỗ trợ.")

    # Tạo notebook hoặc lấy notebook đã tồn tại
    new_notebook = Notebook(title=valid_files[0].filename, user_id=current_user.id)
    new_notebook = notebook_service.add(new_notebook, db)
    
    # Xử lý các file hợp lệ
    success_file = []
    for file in valid_files:
        file_name = file.filename
        unique_filename = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        file_path = os.path.join(config.static_dir, unique_filename + file_extension)
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        bytes, hash = get_bytes_and_hash(file_path)
        source = Source(
            title=file_name,
            filename=file_name,
            file_path=file_path,
            file_hash=hash
        )
        source = source_service.add(source, db)

        notebook_source = NotebookSource(notebook_id=new_notebook.id, source_id=source.id)
        notebook_source_service.add(notebook_source, db)
        
        flat_sections = docling_service.file_to_flat_sections(file_path)

    if success_file:
        return {
            "notebook": jsonable_encoder(new_notebook),
            "success_files": [jsonable_encoder(source) for source in success_file],
            "failed_files": failed_files, 
        }
    else:
        db.rollback()
        return {
            "notebook": None,
            "success_files": [],
            "failed_files": failed_files
        }
    
@router.delete("")
def delete_notebook(
    notebook_id: int,
    db: Session = Depends(get_db), 
    current_user: User = Depends(UserService.get_current_user)
):
    notebook_service.delete(notebook_id, db)
    return {"status": "deleted"}