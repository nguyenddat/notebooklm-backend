from dataclasses import dataclass
from typing import List, Optional, Literal

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, \
    PointStruct, Filter, FieldCondition, MatchValue, MatchAny, \
    SearchParams

from core import config, logger, openai_embeddings
from .data_models import QdrantBaseDocument

@dataclass
class QdrantService:
    collection_name: str
    vector_size: int
    distance: Distance = Distance.COSINE
    recreate: bool = False

    def __post_init__(self):
        self.client = QdrantClient(url=config.qdrant_url)
        self._ensure_collection()

    def insert_chunks(self, documents: List[QdrantBaseDocument], embeddings: List[List[float]]):
        if len(documents) != len(embeddings):
            raise ValueError("Số lượng documents và embeddings phải bằng nhau.")
        
        points: List[PointStruct] = []
        for doc, embedding in zip(documents, embeddings):
            payload = doc.model_dump(exclude={"id"})
            points.append(
                PointStruct(
                    id=doc.id,
                    vector=embedding,
                    payload=payload,
                )
            )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info(f"Inserted {len(points)} points to {self.collection_name}")
        return {"status": "inserted", "points": len(points)}
        

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
        
    def search(self, query: str, top_k: int = 10, source_ids: Optional[List[str]] = None, type: Literal["text", "image"] = None):
        # Embed query
        query_embedding = openai_embeddings.embed_query(query)
        
        # Filter
        must_filters = []
        if source_ids:
            must_filters.append(FieldCondition(key="source_id", match=MatchAny(any=source_ids)))
        if type:
            must_filters.append(FieldCondition(key="type", match=MatchValue(value=type)))
        
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=Filter(must=must_filters) if must_filters else None,
            search_params=SearchParams(hnsw_ef=128),
        )
        return [
            {
                "chunk_id": str(r.id),
                "score": r.score,
                "content": r.payload.get("content", ""),
                "type": r.payload.get("type", "text"),
                "metadata": r.payload.get("metadata", {})
            }
            for r in results.points
        ]

qdrant_service = QdrantService(
    collection_name=config.qdrant_collection_name,
    vector_size=config.qdrant_embedding_dim,
    recreate=False,
)