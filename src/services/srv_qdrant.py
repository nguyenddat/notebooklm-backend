import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, \
    PointStruct, Filter, FieldCondition, MatchValue, MatchAny, \
    SearchParams

from core import config


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

        if exists and not self.recreate:
            return

        if exists and self.recreate:
            self.client.delete_collection(self.collection_name)

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=self.distance,
            ),
        )

        # Index để filter doc_id
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="doc_id",
            field_schema="keyword",
        )

    def insert_chunks(self, chunks: List[Dict]):
        points: List[PointStruct] = []

        for chunk in chunks:
            point_id = chunk.get("chunk_id") or str(uuid.uuid4())

            payload = {
                "source_id": str(chunk["source_id"]),
                "notebook_id": chunk.get("notebook_id"),
                "text": chunk["text"],
                "index": chunk["index"],
                "type": chunk["type"],
                **chunk.get("metadata", {})
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=chunk["embedding"],
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        return {"status": "inserted", "points": len(points)}

    def delete_chunks(
        self,
        doc_id: Optional[str] = None,
        chunk_ids: Optional[List[str]] = None,
    ):
        if not doc_id and not chunk_ids:
            raise ValueError("Không có doc_id hoặc chunk_ids")

        # Xoá toàn bộ document
        if doc_id:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=doc_id),
                        )
                    ]
                ),
            )

            return {"status": "deleted", "doc_id": doc_id,}

        if chunk_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=chunk_ids,
            )

            return {"status": "deleted", "chunk_ids": chunk_ids}
        
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        doc_ids: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
    ):
        must_conditions = []

        if doc_ids:
            must_conditions.append(
                FieldCondition(
                    key="source_id",
                    match=MatchAny(any=doc_ids),
                )
            )

        if types:
            must_conditions.append(
                FieldCondition(
                    key="type",
                    match=MatchAny(any=types),  # ["text"], ["image"], ["text", "image"]
                )
            )

        query_filter = Filter(must=must_conditions) if must_conditions else None

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            search_params=SearchParams(hnsw_ef=128),
        )

        return [
            {
                "chunk_id": r.id,
                "score": r.score,
                "payload": r.payload,
                "index": r.payload.get("index"),
                "text": r.payload.get("text"),
                "type": r.payload.get("type"),
                "image_path": r.payload.get("image_path"),
                "source_id": r.payload.get("source_id"),
                "page": r.payload.get("page"),
            }
            for r in results
        ]

qdrant_service = QdrantService(
    collection_name=config.qdrant_collection_name,
    vector_size=config.qdrant_embedding_dim,
    recreate=False,
)