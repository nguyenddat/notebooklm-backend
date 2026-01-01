from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core import config
from models.model_base import Base
import models

engine = create_engine(config.database_url, pool_pre_ping=True)
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()