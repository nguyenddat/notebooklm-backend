import uuid
from typing import Optional, List

from docling.document_converter import DocumentConverter
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.llm import openai_embeddings
from services import qdrant_service

class RetrieveService:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.converter = DocumentConverter()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""],
        )
    
    def load_to_markdown(self, file_path: str):
        result = self.converter.convert(file_path)
        pages = []

        for page_number, page in result.document.pages.items():
            pages.append({
                "page": page_number,
                "markdown": page.to_markdown(),
            })

        return pages
    
    def markdown_to_documents(self, pages):
        documents = []
        for page in pages:
            page_docs = self.splitter.create_documents(
                [page["markdown"]],
                metadatas=[{"page": page["page"]}],
            )
            documents.extend(page_docs)

        return documents
    
    def index_source(self, source_id: int, file_path: str, notebook_id: Optional[int] = None):        
        pages = self.load_to_markdown(file_path)
        documents = self.markdown_to_documents(pages)
        
        # Tạo embeddings
        texts = [doc.page_content for doc in documents]
        embeddings = openai_embeddings.embed_documents(texts)
        
        # Tạo chunk gồm embedding và metadata
        chunks = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            payload = {
                "chunk_id": str(uuid.uuid4()),
                "chunk_index": i,
                "doc_id": source_id,
                "page": int(doc.metadata["page"]),
                "text": doc.page_content,
                "embedding": embedding,
            }
            if notebook_id is not None:
                payload["notebook_id"] = notebook_id
            
            chunks.append(payload)
            
        return qdrant_service.insert_chunks(chunks)
    
    def retrieve(self, query: str, top_k: int=5, doc_ids: Optional[List[int]]=None, notebook_id: Optional[int]=None):
        query_embedding = openai_embeddings.embed_query(query)
        return qdrant_service.search(
            query_embedding=query_embedding,
            top_k=top_k,
            doc_ids=doc_ids,
            notebook_id=notebook_id,
        )

retrieve_service = RetrieveService(chunk_size=2000, chunk_overlap=200)
