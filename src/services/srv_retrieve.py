import uuid
import matplotlib.pyplot as plt
from typing import Optional, List
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import ImageOps
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from core.llm import openai_embeddings, latex_ocr
from utils.image_caption import pil_to_data_url
from services.srv_qdrant import qdrant_service
from services.srv_llm import llm_service

class RetrieveService:

    EMBED_BATCH = 64
    MIN_IMAGE_AREA = 500
    CONTEXT_BUFFER_SIZE = 5

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self._init_converter()
        self._init_splitters(chunk_size, chunk_overlap)

        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def _init_converter(self):
        options = PdfPipelineOptions()
        options.generate_page_images = True
        options.generate_picture_images = True
        format_option = {InputFormat.PDF: PdfFormatOption(pipeline_options=options)}

        self.converter = DocumentConverter(format_options=format_option)
    
    def _init_splitters(self, chunk_size: int, chunk_overlap: int):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""],
        )

    def load_to_docling_items(self, file_path: str):
        result = self.converter.convert(file_path)
        return result
    
    def docling_items_to_documents(self, result):
        context_buffer = deque(maxlen=self.CONTEXT_BUFFER_SIZE)

        page_buffers = {}
        image_futures = {}
        anchor_results = {}

        for item, _ in result.document.iterate_items():
            label = item.__class__.__name__
            prov = item.prov[0] if item.prov else None
            page_no = prov.page_no if prov else 1
            page_buffers.setdefault(page_no, "")

            content = ""
            if label == "SectionHeaderItem":
                content = f"\n## {item.text.strip()}\n"
                context_buffer.clear()
                context_buffer.append(item.text.strip())

            elif label == "TextItem" and item.text:
                content = item.text.strip() + "\n"
                context_buffer.append(item.text.strip())

            elif label == "TableItem":
                table_md = item.export_to_markdown(doc=result.document)
                content = f"\n[Dữ liệu bảng]\n{table_md}\n"
                context_buffer.append(table_md)

            elif label == "PictureItem":
                img = item.get_image(result)
                if not img or img.size[0] * img.size[1] < self.MIN_IMAGE_AREA:
                    continue
                
                anchor_id = str(uuid.uuid4())
                content = f"[IMAGE:{anchor_id}]\n"

                params = {
                    "question": "\n".join(context_buffer),
                    "image_base64": pil_to_data_url(img),
                    "mime_type": "image/png",
                }

                future = self.executor.submit(
                    llm_service.get_chat_completion,
                    "image_captioning",
                    params,
                )
                image_futures[future] = anchor_id

            elif label == "FormulaItem":
                page = result.pages[page_no - 1]
                page_img = page.get_image()
                img_w, img_h = page_img.size
                bbox = prov.bbox
                area = abs(bbox.r - bbox.l) * abs(bbox.t - bbox.b)
                if area < self.MIN_IMAGE_AREA:
                    continue

                crop_box = (
                    int(bbox.l),
                    int(img_h - bbox.t),
                    int(bbox.r),
                    int(img_h - bbox.b),
                )
                formula_img = ImageOps.expand(
                    page_img.crop(crop_box),
                    border=10,
                    fill="white",
                )

                latex = latex_ocr(formula_img)
                content = f"\n[Công thức]\n$$ {latex} $$\n"

            if content:
                page_buffers[page_no] += content

        for future in as_completed(image_futures):
            aid = image_futures[future]
            try:
                result_text = future.result(timeout=30)["description"]
            except Exception:
                result_text = "Không thể trích xuất mô tả hình ảnh."
            anchor_results[aid] = f"> **Hình ảnh:** {result_text}"

        documents = []
        for page_no, text in page_buffers.items():
            for aid, val in anchor_results.items():
                text = text.replace(f"[IMAGE:{aid}]", val)

            documents.append(
                Document(
                    page_content=text.strip(),
                    metadata={"page": page_no},
                )
            )
        return documents
    
    def merge_short_chunks(self, docs: List[Document], min_chars: int = 500):
        merged = []
        buffer_text = ""
        buffer_page = None

        for doc in docs:
            page = doc.metadata.get("page")

            if not buffer_text:
                buffer_text = doc.page_content
                buffer_page = page
                continue

            if page == buffer_page and len(buffer_text) < min_chars:
                buffer_text += "\n" + doc.page_content
            else:
                merged.append(
                    Document(
                        page_content=buffer_text.strip(),
                        metadata={"page": buffer_page},
                    )
                )
                buffer_text = doc.page_content
                buffer_page = page

        if buffer_text:
            merged.append(
                Document(
                    page_content=buffer_text.strip(),
                    metadata={"page": buffer_page},
                )
            )

        return merged

    def index_source(
        self,
        source_id: int,
        file_path: str,
        notebook_id: Optional[int] = None,
    ):
        result = self.converter.convert(file_path)
        raw_docs = self.docling_items_to_documents(result)

        split_docs = self.merge_short_chunks(
            self.splitter.split_documents(raw_docs)
        )

        texts = [doc.page_content for doc in split_docs]
        embeddings = []

        for i in range(0, len(texts), self.EMBED_BATCH):
            embeddings.extend(
                openai_embeddings.embed_documents(
                    texts[i : i + self.EMBED_BATCH]
                )
            )

        chunks = []
        for idx, (doc, emb) in enumerate(zip(split_docs, embeddings)):
            payload = {
                "chunk_id": str(uuid.uuid4()),
                "chunk_index": idx,
                "doc_id": source_id,
                "page": doc.metadata["page"],
                "text": doc.page_content,
                "embedding": emb,
            }
            if notebook_id:
                payload["notebook_id"] = notebook_id
            chunks.append(payload)

        return qdrant_service.insert_chunks(chunks)
        
    def retrieve(self, query: str, top_k: int=5, doc_ids: Optional[List[int]]=None, notebook_id: Optional[int]=None):
        query_embedding = openai_embeddings.embed_query(query)
        return qdrant_service.search(
            query_embedding=query_embedding,
            top_k=top_k,
            doc_ids=doc_ids,
        )

    def delete_source(self, source_id: int, notebook_id: Optional[int] = None):
        qdrant_service.delete_chunks(source_id, notebook_id)

retrieve_service = RetrieveService(chunk_size=1500, chunk_overlap=200)