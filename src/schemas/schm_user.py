from pydantic import BaseModel

class UserCreateRequest(BaseModel):
    email: str
    password: str