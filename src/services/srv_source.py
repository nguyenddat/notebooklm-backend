from sqlalchemy.orm import Session

from models.entities import Source
from services.srv_base import BaseService

class SourceService(BaseService[Source]):
    def __init__(self, model: type[Source]):
        super().__init__(model)
    
    def get_source_by_file_hash(self, file_hash: str, db: Session):
        return db.query(Source).filter(Source.file_hash == file_hash).first()

source_service = SourceService(Source)