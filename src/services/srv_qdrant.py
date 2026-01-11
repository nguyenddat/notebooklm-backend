from dataclasses import dataclass
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, \
    PointStruct, Filter, FieldCondition, MatchValue, MatchAny, \
    SearchParams

from core import config
from utils.utils_qdrant import QdrantPayload, IndexedChunk, SearchResult

@dataclass
class QdrantService:
    collection_name: str
    vector_size: int
    distance: Distance = Distance.COSINE
    recreate: bool = False

    def __post_init__(self):
        self.client = QdrantClient(url=config.qdrant_url)
        self._ensure_collection()

    def _ensure_collection(self):
        exists = self.client.collection_exists(self.collection_name)

        if exists:
            if not self.recreate:
                return
            self.client.delete_collection(self.collection_name)

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=self.distance,
            ),
        )

        # Index để filter theo source_id
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="source_id",
            field_schema="keyword",
        )

    def insert_chunks(self, chunks: List[IndexedChunk]):
        points: List[PointStruct] = []

        for chunk in chunks:
            payload = QdrantPayload(
                source_id=chunk.source_id,
                notebook_id=chunk.notebook_id,
                chunk_id=chunk.chunk_id,
                index=chunk.index,
                type=chunk.type,
                text=chunk.text,
                image_path=chunk.image_path,
                page=chunk.page,
                breadcrumb=chunk.breadcrumb,
            )

            points.append(
                PointStruct(
                    id=chunk.chunk_id,
                    vector=chunk.embedding,
                    payload=payload.model_dump(exclude_none=True),
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        return {"status": "inserted", "points": len(points)}

    def delete_by_source(self, source_id: str):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source_id",
                        match=MatchValue(value=source_id),
                    )
                ]
            ),
        )
        return {"status": "deleted", "source_id": source_id}

    def delete_by_chunk_ids(self, chunk_ids: List[str]):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=chunk_ids,
        )
        return {"status": "deleted", "chunk_ids": chunk_ids}
        
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        source_ids: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
    ) -> List[SearchResult]:

        must = []
        if source_ids:
            must.append(
                FieldCondition(
                    key="source_id",
                    match=MatchAny(any=source_ids),
                )
            )

        if types:
            must.append(
                FieldCondition(
                    key="type",
                    match=MatchAny(any=types),
                )
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=Filter(must=must) if must else None,
            search_params=SearchParams(hnsw_ef=128),
        )

        return [
            SearchResult(
                chunk_id=r.id,
                score=r.score,
                source_id=r.payload["source_id"],
                type=r.payload["type"],
                text=r.payload["text"],
                image_path=r.payload.get("image_path"),
                page=r.payload.get("page"),
                breadcrumb=r.payload.get("breadcrumb"),
            )
            for r in results
        ]

qdrant_service = QdrantService(
    collection_name=config.qdrant_collection_name,
    vector_size=config.qdrant_embedding_dim,
    recreate=False,
)