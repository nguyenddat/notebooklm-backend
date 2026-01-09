from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from models.model_base import BareBaseModel

class Source(BareBaseModel):
    title = Column(String, nullable=True)
    filename = Column(String, nullable=False)

    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False)

    structure_config = Column(JSON, nullable=True)
    
    # Source - Notebook
    notebook_source = relationship("NotebookSource", back_populates="source")