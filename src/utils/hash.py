import re
import hashlib
import unicodedata
from pathlib import Path
from typing import Union

def get_bytes_and_hash(file: Union[bytes, str, Path]):
    if isinstance(file, (str, Path)):
        path = Path(file)
        if not path.exists():
            raise FileNotFoundError(f"Path {file} không tồn tại")
        content = path.read_bytes()
    elif isinstance(file, bytes):
        content = file
    else:
        raise TypeError("File phải là bytes, str hoặc Path")
    
    file_hash = hashlib.sha256(content).hexdigest()
    return content, file_hash

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = " ".join(text.split())
    return text.strip()