from typing import Union, Any, Optional
from datetime import datetime, timedelta

from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from core import config
from database import get_db
from models.entities.model_user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
class UserService:
    @staticmethod
    def authenticate(form_data, db: Session):
        email = form_data.username
        password = form_data.password

        user = UserService.get_user_by_email(email, db)
        if not user:
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
        
        if not UserService.verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

        return user        

    @staticmethod
    def create_user(user: User, db: Session):
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ):
        credentials_exception = HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, config.secret_key, algorithms=[config.security_algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = db.query(User).filter(User.email == user_id).first()
        if user is None:
            raise credentials_exception

        return user

    @staticmethod
    def get_user_by_email(email: str, db: Session):
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create_tokens(user: User):
        access_token = UserService.create_access_token(user.email)
        refresh_token = UserService.create_refresh_token(user.email)
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=config.access_token_expire_minutes)
        
        to_encode = {"exp": expire, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, config.secret_key, algorithm=config.security_algorithm)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(subject: Union[str, Any]) -> str:
        expire = datetime.utcnow() + timedelta(days=config.refresh_token_expire_days)
        to_encode = {"exp": expire, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, config.secret_key, algorithm=config.security_algorithm)
        return encoded_jwt