from collections import deque
from collections import defaultdict

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core import logger
from services.source.data_models import SectionNode
from services.qdrant.data_models import QdrantBaseDocument, QdrantDocumentMetadata

class ContextualDocumentService:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "],
        )

    def build_documents(self, roots: list[SectionNode]) -> list[QdrantBaseDocument]:
        logger.info("ContextualDocument: start building documents")
        
        linear_nodes = self.flatten_tree(roots)
        logger.info("Flattened tree into %d linear nodes", len(linear_nodes))
        
        node_index = {n.order_id: n for n in linear_nodes}
        leaf_groups = self.group_leaves_by_parent(linear_nodes)
        logger.info("Grouped %d leaf groups (by parent_id)", len(leaf_groups),)

        documents: list[QdrantBaseDocument] = []
        for parent_id, leaves in leaf_groups.items():
            logger.info("ContextualDocument: built %d documents for indexing", len(documents))
            documents.extend(
                self.chunk_leaf_group(parent_id, leaves, node_index)
            )
            
        # Cần build thêm document ảnh
        image_leaves = [node for node in linear_nodes if node.is_image()]
        for img_node in image_leaves:
            breadcrumb = self.build_breadcrumb(img_node.parent_id, node_index)
            
            caption = img_node.caption
            if caption:
                content = self.compose_chunk_text(img_node.caption, breadcrumb)
            else:
                logger.info(f"ContextualDocument: Image node {breadcrumb}-{img_node.image_path} does not have caption. SKIP!")
                content = "[Image without description]"
            
            documents.append(QdrantBaseDocument(
                content=content,
                type="image",
                metadata=QdrantDocumentMetadata(
                    page_start=img_node.page,
                    page_end=img_node.page,
                    breadcrumb=breadcrumb,
                    image_path=img_node.image_path,
                    image_caption=caption
                )
            ))

        return documents

    # Tree utilities
    def flatten_tree(self, roots: list[SectionNode]) -> list[SectionNode]:
        queue = deque(roots)
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            queue.extend(sorted(node.children, key=lambda n: n.order_id))

        return result

    def group_leaves_by_parent(
        self,
        nodes: list[SectionNode],
    ) -> dict[int | None, list[SectionNode]]:
        groups = defaultdict(list)

        for node in nodes:
            if not node.children:
                groups[node.parent_id].append(node)

        return groups

    # Chunking
    def chunk_leaf_group(
        self,
        parent_id: int | None,
        leaves: list[SectionNode],
        node_index: dict[int, SectionNode],
    ) -> list[QdrantBaseDocument]:
        leaves = sorted(leaves, key=lambda n: n.order_id)
        raw_text = self.compose_group_text(leaves)
        chunks = self.splitter.split_text(raw_text)

        breadcrumb = self.build_breadcrumb(parent_id, node_index)

        documents = []
        for chunk in chunks:
            documents.append(QdrantBaseDocument(
                    content=self.compose_chunk_text(chunk, breadcrumb),
                    type="text",
                    source_id=None,
                    metadata=QdrantDocumentMetadata(
                        page_start=leaves[0].page,
                        page_end=leaves[-1].page,
                        breadcrumb=breadcrumb
                    )
                )
            )

        return documents

    # Text composition
    def compose_group_text(self, leaves: list[SectionNode]) -> str:
        parts = []
        for node in leaves:
            if node.content:
                parts.append(node.content.strip())
        return "\n\n".join(parts)

    def compose_chunk_text(self, chunk: str, breadcrumb: list[str]) -> str:
        parts = []

        if breadcrumb:
            parts.append("# Mục")
            parts.append(" > ".join(breadcrumb))

        parts.append("\n# Nội dung")
        parts.append(chunk.strip())

        return "\n".join(parts)

    # Breadcrumb
    def build_breadcrumb(self, parent_id: int | None, node_index: dict[int, SectionNode]) -> list[str]:
        titles = []
        cur_id = parent_id

        while cur_id:
            node = node_index.get(cur_id)
            if not node:
                break

            if node.is_header() and node.title:
                titles.append(node.title.strip())

            cur_id = node.parent_id

        return list(reversed(titles))

contextual_document_service = ContextualDocumentService()