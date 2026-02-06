import os
import uuid
import shutil
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.encoders import jsonable_encoder

from core import config, logger
from database import get_db
from models.entities import User, Notebook, Source
from models.relationship import NotebookSource
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
    # Check định dạng: chỉ hỗ trợ pdf và docx
    valid_files = []
    invalid_format_files = []
    
    for file in files:
        if check_valid_file_type(file.content_type):
            valid_files.append(file)
        else:
            invalid_format_files.append(file.filename)
            logger.warning(f"File '{file.filename}' không đúng định dạng hỗ trợ (pdf/docx)")
    
    # Nếu không có file nào hợp lệ -> fail ngay
    if not valid_files:
        raise HTTPException(
            status_code=400, 
            detail=f"Không file nào hợp lệ. Chỉ hỗ trợ định dạng PDF và DOCX. Files bị từ chối: {invalid_format_files}"
        )

    # Tạo notebook mới
    new_notebook = Notebook(title=valid_files[0].filename, user_id=current_user.id)
    new_notebook = notebook_service.add(new_notebook, db)
    
    # Xử lý từng file hợp lệ
    success_files = []
    failed_files = list(invalid_format_files)  # Bắt đầu với các file sai định dạng
    saved_paths = []  # Track các file đã lưu để cleanup khi fail
    

    for file in valid_files:
        file_name = file.filename
        unique_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # Chuẩn hóa đường dẫn lưu file
        saved_filename = f"{unique_id}{file_extension}"
        file_path = os.path.join(config.static_dir, saved_filename)
        file_images_dir = os.path.join(config.static_dir, unique_id)
        
        # Lưu file vào disk
        try:
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            saved_paths.append((file_path, file_images_dir))  # Track để cleanup
        except Exception as e:
            logger.error(f"Lỗi lưu file '{file_name}': {e}")
            failed_files.append(file_name)
            continue
        
        # DB chỉ lưu tên file unique, không lưu full path
        source = Source(
            title=file_name, 
            filename=file_name, 
            file_path=saved_filename
        )
        source = source_service.add(source, db)

        # Link notebook với source
        notebook_source = NotebookSource(notebook_id=new_notebook.id, source_id=source.id)
        notebook_source_service.add(notebook_source, db)
        
        try:
            result = source_service.process_file(file_path, file_name, source.id, file_images_dir)
            if result:
                success_files.append(file_name)
                logger.info(f"Xử lý file '{file_name}' thành công")
            else:
                failed_files.append(file_name)
                logger.warning(f"Xử lý file '{file_name}' trả về False")
        except Exception as e:
            logger.error(f"Lỗi xử lý file '{file_name}': {e}")
            failed_files.append(file_name)
            continue
    
    # Kiểm tra kết quả
    if not success_files:
        # Cleanup: xóa static files đã lưu
        for file_path, images_dir in saved_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Đã xóa file: {file_path}")
                if os.path.exists(images_dir):
                    shutil.rmtree(images_dir)
                    logger.info(f"Đã xóa thư mục: {images_dir}")
            except Exception as e:
                logger.error(f"Lỗi xóa file/folder: {e}")
        
        # Cleanup: xóa notebook trong DB
        try:
            notebook_service.delete(new_notebook.id, db)
            logger.info(f"Đã xóa notebook {new_notebook.id} do không có file nào xử lý thành công")
        except Exception as e:
            logger.error(f"Lỗi khi xóa notebook {new_notebook.id}: {e}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Xử lý thất bại tất cả files. Files lỗi: {failed_files}"
        )
    
    # Có ít nhất 1 file thành công -> thành công
    return {
        "notebook": jsonable_encoder(new_notebook),
        "success_files": success_files,
        "failed_files": failed_files if failed_files else None,
    }
    
@router.delete("")
def delete_notebook(
    notebook_id: int,
    db: Session = Depends(get_db), 
    current_user: User = Depends(UserService.get_current_user)
):
    notebook_service.delete(notebook_id, db)
    return {"status": "deleted"}