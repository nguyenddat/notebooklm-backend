import hashlib

def hash_file(file_obj) -> str:
    file_obj.seek(0)               
    content = file_obj.read()
    file_obj.seek(0)               
    return hashlib.sha256(content).hexdigest()