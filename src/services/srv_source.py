from sqlalchemy.orm import Session

from models.entities import Source
from models.relationship import NotebookSource
from services.srv_base import BaseService

class SourceService(BaseService[Source]):
    def __init__(self, model: type[Source]):
        super().__init__(model)
    
    def get_source_by_file_hash(self, file_hash: str, db: Session):
        return db.query(Source).filter(Source.file_hash == file_hash).first()
    
    def get_sources_by_notebook_id(self, notebook_id: int, db: Session):
        notebook_sources = db.query(NotebookSource).filter(NotebookSource.notebook_id == notebook_id).all()
        if not notebook_sources:
            return []
        
        sources = []        
        for ns in notebook_sources:
            sources.append(
                db.query(Source).filter(Source.id == ns.source_id).first()
            )
        return sources

source_service = SourceService(Source)