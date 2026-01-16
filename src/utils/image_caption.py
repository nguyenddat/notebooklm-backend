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
    valid_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
    ]

    if file_type not in valid_types:
        return False
    return True