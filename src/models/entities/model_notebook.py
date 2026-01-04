from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from models.model_base import BareBaseModel

class Notebook(BareBaseModel):
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    
    # Notebook - User & Message
    user = relationship("User", back_populates="notebook")
    message = relationship("Message", back_populates="notebook")
    notebook_source = relationship("NotebookSource", back_populates="notebook")