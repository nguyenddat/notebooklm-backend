import base64
from io import BytesIO
from PIL import Image


def pil_to_data_url(image: Image.Image, fmt: str = "PNG") -> str:
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/{fmt.lower()};base64,{encoded}"

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