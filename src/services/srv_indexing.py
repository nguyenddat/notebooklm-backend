import uuid
import logging
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core import openai_embeddings
from services.srv_qdrant import qdrant_service
from utils.utils_docling.models import SectionNode
from utils.utils_qdrant import IndexedChunk
from utils.utils_docling.formatting import collect_section_texts

logger = logging.getLogger(__name__)

class IndexingService:
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.splitter = self._init_splitter(chunk_size, chunk_overlap)
        logger.info(f"Initialized IndexingService with chunk_size={chunk_size}")

    def index(self, source_id: int, tree: List[SectionNode], notebook_id: Optional[int] = None):
        logger.info(f"Indexing source_id={source_id} with text + image chunks")

        sections = collect_section_texts(tree)
        if not sections:
            return {"status": "empty", "points": 0}

        all_chunks: List[IndexedChunk] = []

        for sec in sections:
            # Skip image items in text loop
            if sec.get("type") == "image":
                continue

            section_prefix = f"[Section: {sec['breadcrumb']}]\n"
            chunks = [section_prefix + chunk for chunk in self.splitter.split_text(sec["text"])]
            embeddings = openai_embeddings.embed_documents(chunks)

            for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
                if not chunk_text:
                    logger.warning(f"Empty chunk at index {i} for section {sec['breadcrumb']}")
                    continue

                all_chunks.append(
                    IndexedChunk(
                        chunk_id=str(uuid.uuid4()),
                        source_id=str(source_id),
                        notebook_id=notebook_id,
                        text=chunk_text,
                        index=sec["section_index"],
                        type="text",
                        embedding=emb,
                        breadcrumb=sec["breadcrumb"],
                    )
                )
                
        # INDEX IMAGE CHUNKS
        image_items = [
            n for n in sections
            if n.get("type") == "image"
            and isinstance(n.get("text"), str)
            and n["text"].strip()
        ]

        if image_items:
            captions = [
                f"[Section: {sec['breadcrumb']}]\n{sec['text']}"
                for sec in image_items
            ]
            image_embeddings = openai_embeddings.embed_documents(captions)

            for sec, emb in zip(image_items, image_embeddings):
                if not sec["text"]:
                    logger.warning(f"Empty image chunk at index {i} for section {sec['breadcrumb']}")
                    continue

                all_chunks.append(
                    IndexedChunk(
                        chunk_id=str(uuid.uuid4()),
                        source_id=str(source_id),
                        notebook_id=notebook_id,
                        text=sec["text"],
                        index=sec["section_index"],
                        embedding=emb,
                        type="image",
                        page=sec["page"],
                        image_path=sec["image_path"],
                        breadcrumb=sec["breadcrumb"],
                    )
                )

        logger.info(f"Indexed {len(all_chunks)} total chunks (text + image)")
        return qdrant_service.insert_chunks(all_chunks)

    def _init_splitter(self, chunk_size, chunk_overlap) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""]
        )

indexing_service = IndexingService()
