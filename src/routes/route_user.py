from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from schemas import UserCreateRequest
from models.entities.model_user import User
from services import UserService

router = APIRouter()

@router.post("/register")
def create_user(request: UserCreateRequest, db: Session = Depends(get_db)):
    check_by_email = UserService.get_user_by_email(request.email, db)
    if check_by_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    try:
        user = User(email = request.email, password_hash = UserService.hash_password(request.password))
        user = UserService.create_user(user, db)
        
        # Create tokens
        access_token = UserService.create_access_token(user.email)
        refresh_token = UserService.create_refresh_token(user.email)
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    
    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = UserService.authenticate(form_data=request, db=db)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = UserService.create_access_token(user.email)
    refresh_token = UserService.create_refresh_token(user.email)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.get("/me")
def get_current_user(current_user: User = Depends(UserService.get_current_user)):
    current_user = jsonable_encoder(current_user)
    return JSONResponse(status_code=200, content=current_user)