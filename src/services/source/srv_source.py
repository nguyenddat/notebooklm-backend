from pathlib import Path
from typing import Union, List

from sqlalchemy.orm import Session

from core import openai_embeddings, logger
from models.entities import Source
from models.relationship import NotebookSource
from utils import get_bytes_and_hash
from services.srv_base import BaseService
from services.redis import RedisKeys, redis_service
from services.source import docling_service, tree_builder, \
    image_caption_service, contextual_document_service, SectionNode
from services.qdrant import qdrant_service, QdrantBaseDocument

class SourceService(BaseService[Source]):
    def __init__(self, model: type[Source]):
        super().__init__(model)
        self.embedding_batch = 128
    
    def process_file(self, file: Union[bytes, str, Path], source_id: int) -> bool:
        file = Path(file)
        
        # Check cache
        _, file_hash = get_bytes_and_hash(file)
        cache_key = RedisKeys.flat_sections(file_hash)
        
        cached = redis_service.get_object(cache_key)
        if cached:
            logger.info(f"Flat-sections cache hit: {file_hash[:10]}")
            # return True
            
        # Chuyển từ file sang Flat Section List
        flat_sections: List[SectionNode] =  docling_service.file_to_flat_sections(file)
        
        # Build tree -> Caption ảnh
        roots: List[SectionNode] = tree_builder.build(flat_sections)
        image_caption_service.process(roots)
        
        # Chuyển thành documents
        documents: List[QdrantBaseDocument] = contextual_document_service.build_documents(roots)
        for doc in documents:
            doc.source_id = source_id
        
        # Embeddings
        all_contents = [doc.content for doc in documents]
        embeddings = []
        for i in range(0, len(all_contents), self.embedding_batch):
            batch_texts = all_contents[i : i + self.embedding_batch]
            batch_embeddings = openai_embeddings.embed_documents(batch_texts)
            embeddings.extend(batch_embeddings)
            
        # Insert vào vector db
        qdrant_service.insert_chunks(documents, embeddings)
        
        # Save cache
        redis_service.set_object(cache_key, flat_sections)
        logger.info("Done")
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