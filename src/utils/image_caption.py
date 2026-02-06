import os
import base64
from io import BytesIO
from PIL import Image

def image_path_to_data_url(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as img:
        fmt = (img.format or "PNG").lower()

        buffer = BytesIO()
        img.save(buffer, format=img.format or "PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/{fmt};base64,{encoded}"

def check_valid_file_type(file_type) -> bool:
    """Chỉ hỗ trợ PDF và DOCX"""
    valid_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    return file_type in valid_types


def normalize_static_path(file_path: str) -> str:
    """Chuẩn hóa path, loại bỏ prefix không cần thiết như app/static/"""
    if not file_path:
        return ""
    
    # Loại bỏ các prefix không mong muốn
    prefixes_to_remove = ["app/static/", "/app/static/", "static/", "/static/"]
    for prefix in prefixes_to_remove:
        if file_path.startswith(prefix):
            file_path = file_path[len(prefix):]
            break
    
    return file_path