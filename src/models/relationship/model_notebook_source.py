from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from models.model_base import BareBaseModel

class NotebookSource(BareBaseModel):
    notebook_id = Column(Integer, ForeignKey("notebook.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("source.id", ondelete="CASCADE"), nullable=False)
    
    # ConversationSource - Notebook & Source
    notebook = relationship("Notebook", back_populates="notebook_source")
    source = relationship("Source", back_populates="notebook_source")