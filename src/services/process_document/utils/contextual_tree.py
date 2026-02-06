from collections import deque
from typing import List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core import logger
from .data_models import SectionNode
from services.qdrant.data_models import QdrantBaseDocument, QdrantDocumentMetadata


class ContextualDocumentService:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "],
        )
    
    def convert_tree_to_documents(self, roots: list[SectionNode]) -> list[QdrantBaseDocument]:
        logger.info("-" * 50)
        logger.info("ContextualDocument: start building documents")
        logger.info("-" * 50)

        documents: list[QdrantBaseDocument] = []
        
        # Duyệt BFS qua tree
        queue = deque()
        for root in roots:
            # Khởi tạo breadcrumb cho root
            root_breadcrumb = [root.content] if root.is_header() else []
            queue.append((root, root_breadcrumb))
        
        while queue:
            node, current_breadcrumb = queue.popleft()
            
            if node.is_header():
                # Xử lý header node: cộng dồn text con, tách image riêng
                header_docs = self._process_header_node(node, current_breadcrumb)
                documents.extend(header_docs)
                
                # Thêm children header vào queue với breadcrumb cập nhật
                for child in node.children:
                    if child.is_header():
                        child_breadcrumb = current_breadcrumb + [child.content]
                        queue.append((child, child_breadcrumb))
            else:
                # Node không thuộc header nào (root level text/image)
                orphan_docs = self._process_orphan_node(node, current_breadcrumb)
                documents.extend(orphan_docs)

        logger.info("ContextualDocument: built %d documents", len(documents))
        return documents
    
    def _process_header_node(
        self, 
        header: SectionNode, 
        breadcrumb: list[str]
    ) -> list[QdrantBaseDocument]:
        documents: list[QdrantBaseDocument] = []
        
        # Thu thập text và image từ children (chỉ xét node non-header)
        accumulated_text = []
        image_nodes: list[SectionNode] = []
        text_pages: list[int] = []
        
        for child in header.children:
            if child.is_header():
                continue
            elif child.is_image():
                image_nodes.append(child)
            else:
                if child.content.strip():
                    accumulated_text.append(child.content.strip())
                    if child.page is not None:
                        text_pages.append(child.page)
        
        # Tạo breadcrumb string
        breadcrumb_str = self._format_breadcrumb(breadcrumb)
        
        # Xử lý accumulated text -> split thành chunks
        if accumulated_text:
            combined_text = "\n".join(accumulated_text)
            chunks = self.splitter.split_text(combined_text)
            
            page_start = min(text_pages) if text_pages else (header.page or 1)
            page_end = max(text_pages) if text_pages else (header.page or 1)
            
            for chunk in chunks:
                content_with_breadcrumb = f"{breadcrumb_str}\n\n{chunk}" if breadcrumb_str else chunk
                
                doc = QdrantBaseDocument(
                    content=content_with_breadcrumb,
                    type="text",
                    metadata=QdrantDocumentMetadata(
                        file_path=header.file_path or "",
                        filename=header.filename or "",
                        page_start=page_start,
                        page_end=page_end,
                        breadcrumb=breadcrumb,
                    )
                )
                documents.append(doc)
        
        # Xử lý image nodes riêng
        for img_node in image_nodes:
            content_with_breadcrumb = f"{breadcrumb_str}\n\n" if breadcrumb_str else ""
            
            doc = QdrantBaseDocument(
                content=content_with_breadcrumb,
                type="image",
                metadata=QdrantDocumentMetadata(
                    file_path=img_node.file_path or header.file_path or "",
                    filename=img_node.filename or header.filename or "",
                    page_start=img_node.page or header.page or 1,
                    page_end=img_node.page or header.page or 1,
                    breadcrumb=breadcrumb,
                    image_path=img_node.image_path,
                )
            )
            documents.append(doc)
        
        return documents
    
    def _process_orphan_node(
        self, 
        node: SectionNode, 
        breadcrumb: list[str]
    ) -> list[QdrantBaseDocument]:
        documents: list[QdrantBaseDocument] = []
        breadcrumb_str = self._format_breadcrumb(breadcrumb)
        
        if node.is_image():
            content_with_breadcrumb = f"{breadcrumb_str}\n\n" if breadcrumb_str else ""
            
            doc = QdrantBaseDocument(
                content=content_with_breadcrumb,
                type="image",
                metadata=QdrantDocumentMetadata(
                    file_path=node.file_path or "",
                    filename=node.filename or "",
                    page_start=node.page or 1,
                    page_end=node.page or 1,
                    breadcrumb=breadcrumb,
                    image_path=node.image_path,
                )
            )
            documents.append(doc)
        else:
            if node.content.strip():
                chunks = self.splitter.split_text(node.content.strip())
                for chunk in chunks:
                    content_with_breadcrumb = f"{breadcrumb_str}\n\n{chunk}" if breadcrumb_str else chunk
                    
                    doc = QdrantBaseDocument(
                        content=content_with_breadcrumb,
                        type="text",
                        metadata=QdrantDocumentMetadata(
                            file_path=node.file_path or "",
                            filename=node.filename or "",
                            page_start=node.page or 1,
                            page_end=node.page or 1,
                            breadcrumb=breadcrumb,
                        )
                    )
                    documents.append(doc)
        
        return documents
    
    def _format_breadcrumb(self, breadcrumb: list[str]) -> str:
        if not breadcrumb:
            return ""
        return " > ".join(breadcrumb)


contextual_document_service = ContextualDocumentService()