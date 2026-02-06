from typing import List

from .utils import DocImageModel, DocPageModel, SectionNode, \
    ocr_service, image_caption_service, doc_extractor, tree_builder, contextual_document_service
from services.qdrant.data_models import QdrantBaseDocument

class DocumentProcessor:
    def process_document(self, file_path: str, filename: str, output_dir: str) -> List[QdrantBaseDocument]:
        # Đọc file thành các trang ảnh kèm ảnh thành phần tương ứng
        pages = doc_extractor.convert_pdf_to_pages(file_path, output_dir)

        # OCR các trang và chuyển thành các nodes
        flat_nodes = ocr_service.ocr_pages(pages, file_path, filename)

        # Build cây từ các node tương ứng
        tree = tree_builder.build(flat_nodes)

        # Xử lý cây thành các document
        qdrant_documents = contextual_document_service.convert_tree_to_documents(tree)
        return qdrant_documents

document_processor = DocumentProcessor()