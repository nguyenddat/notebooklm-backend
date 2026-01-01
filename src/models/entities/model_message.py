import enum

from sqlalchemy import Column, Integer, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship

from models.model_base import BareBaseModel

class MessageRole(enum.Enum):
    USER="user"
    ASSISTANT="assistant"

class Message(BareBaseModel):
    role = Column(Enum(MessageRole))
    content = Column(Text, nullable=False)
    citations = Column(Text, nullable=True)
    notebook_id = Column(Integer, ForeignKey("notebook.id"), nullable=False)
    
    # Message - Conversation
    notebook = relationship("Notebook", back_populates="message")