from pathlib import Path
from typing import Union, List

from sqlalchemy.orm import Session

from core import logger, openai_embeddings
from models.entities import Source
from models.relationship import NotebookSource
from services.srv_base import BaseService
from services.qdrant import qdrant_service, QdrantBaseDocument

from services.process_document.document_processor import document_processor

class SourceService(BaseService[Source]):
    def __init__(self, model: type[Source]):
        super().__init__(model)
        self.embedding_batch = 128
    
    def process_file(self, file_path: str, file_name: str, source_id: int, output_dir: str) -> bool:
        # Documents
        documents = document_processor.process_document(file_path, file_name, output_dir)
        for doc in documents:
            doc.source_id = source_id

        # Embedding theo batch
        all_contents = [doc.content for doc in documents]
        embeddings = []
        for i in range(0, len(all_contents), self.embedding_batch):
            batch_texts = all_contents[i : i + self.embedding_batch]
            batch_embeddings = openai_embeddings.embed_documents(batch_texts)
            embeddings.extend(batch_embeddings)
        
        # Insert vào vector db
        qdrant_service.insert_chunks(documents, embeddings)
        return True
    
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