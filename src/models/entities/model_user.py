from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from models.model_base import BareBaseModel

class User(BareBaseModel):
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    
    full_name = Column(String)
    
    # User - Notebook
    notebook = relationship("Notebook", back_populates="user")