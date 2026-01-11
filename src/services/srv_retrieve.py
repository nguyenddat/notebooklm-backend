import os
import uuid
import json
import pathlib
import logging

from typing import Optional, List, Union
from concurrent.futures import ThreadPoolExecutor

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core import config, openai_embeddings
from services.srv_qdrant import qdrant_service
from services.srv_llm import llm_service

from utils.image_caption import pil_to_data_url
from utils.utils_docling.models import SectionNode, TextLeaf, ImageLeaf
from utils.utils_docling.structure import process_structure
from utils.utils_docling.postprocess import post_endpage, post_title_context
from utils.utils_docling.formatting import (
    collect_ordered_text,
    build_long_document,
)

logger = logging.getLogger(__name__)

class RetrieveService:
    MAX_CONTEXT_CHARS = 2500
    EMBED_BATCH = 64

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.converter = self._init_converter()
        self.splitter = self._init_splitter(chunk_size, chunk_overlap)
        logger.info(f"Initialized RetrieveService with chunk_size={chunk_size}")


    def process_file(self, source_id: int, file_path: str, notebook_id: Optional[int] = None):
        logger.info(f"Starting processing file: {file_path} (source_id: {source_id})")

        # convert pdf into docling items
        conversion_result = self.converter.convert(file_path)
        logger.info("PDF conversion completed successfully.")
        
        file_basename = pathlib.Path(file_path).stem
        image_save_dir = os.path.join(config.static_dir, f"{file_basename}_{source_id}")
        os.makedirs(image_save_dir, exist_ok=True)
        logger.info(f"Artifact directory created: {image_save_dir}")

        # extracting flat-text structure from docling items
        logger.info("\t1. Extracting flat structure from document items...")
        flat_sections = process_structure(conversion_result, image_save_dir)
        logger.info(f"Extracted {len(flat_sections)} flat sections.")
        
        # building tree-text structure from docling items
        logger.info("\t2. Building hierarchical tree with LLM...")
        hierarchical_tree = self._build_section_hierarchical_tree(flat_sections)
        
        # update end-page for nodes
        logger.info("\t3. Post-process: Cập nhật end_page cho các SectionNode...")
        hierarchical_tree = post_endpage(hierarchical_tree)

        # update title context for nodes
        logger.info("\t4. Post-process: Cập nhật title context cho các SectionNode...")
        hierarchical_tree = post_title_context(hierarchical_tree)

        # update caption for images
        logger.info("\t5. Post-process: Image captioning...")
        self._post_image_process(hierarchical_tree)

        logger.info(f"Successfully processed file: {file_basename}")
        return hierarchical_tree
        
    def retrieve(self, query: str, source_id: int, top_k: int = 5):
        # embedding text
        query_vector = openai_embeddings.embed_query(query)

        # retrieve top-k*2 text leaves
        texts = []
        text_hits = qdrant_service.search(
            query_embedding=query_vector,
            top_k=top_k * 2,
            doc_ids=[str(source_id)],
            types=["text"],
        )
        for hit in text_hits:
            payload = hit["payload"]
            texts.append(payload["text"])
        logger.info(f"Retrieve text hits: {len(text_hits)}")

        # retrieve top_k image leaves
        images = []
        image_hits = qdrant_service.search(
            query_embedding=query_vector,
            top_k=top_k,
            doc_ids=[str(source_id)],
            types=["image"],
        )
        logger.info(f"Retrieve image hits: {len(image_hits)}")

        for hit in image_hits:
            payload = hit["payload"]
            images.append({
                "caption": payload["text"],
                "image_path": payload["image_path"],
                "page": payload.get("page"),
                "breadcrumb": payload.get("breadcrumb"),
            })

        return {
            "texts": texts[:top_k],
            "images": images[:top_k],
        }
    
    def index(self, source_id: int, tree: List[SectionNode], notebook_id: Optional[int] = None):
        logger.info(f"Indexing source_id={source_id} with text + image chunks")

        ordered_nodes = collect_ordered_text(tree)
        if not ordered_nodes:
            return {"status": "empty", "points": 0}

        all_chunks = []

        # INDEX TEXT CHUNKS
        text_items = [n for n in ordered_nodes if n["type"] == "text"]

        if text_items:
            full_doc = build_long_document(text_items)
            chunks = self.splitter.split_text(full_doc)
            embeddings = openai_embeddings.embed_documents(chunks)

            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                all_chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "source_id": str(source_id),
                    "notebook_id": notebook_id,
                    "text": chunk_text,
                    "index": i,
                    "type": "text",
                    "embedding": embedding,
                })

        # INDEX IMAGE CHUNKS
        image_items = [
            n for n in ordered_nodes
            if n["type"] == "image" and n.get("text")
        ]

        if image_items:
            captions = [img["text"] for img in image_items]
            image_embeddings = openai_embeddings.embed_documents(captions)

            for img, emb in zip(image_items, image_embeddings):
                all_chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "source_id": str(source_id),
                    "notebook_id": notebook_id,
                    "text": img["text"],
                    "index": img["index"],
                    "embedding": emb,
                    "type": "image",
                    "metadata": {
                        "page": img["page"],
                        "image_path": img["image_path"],
                        "breadcrumb": img["breadcrumb"],
                    }
                })

        logger.info(f"Indexed {len(all_chunks)} total chunks (text + image)")
        return qdrant_service.insert_chunks(all_chunks)


    def _build_section_hierarchical_tree(self, sections: List[SectionNode]):
        skeleton = self._build_section_skeleton(sections)

        task = "correct_section_structure"
        params = {"sections": json.dumps(skeleton), "question": ""}
        response = llm_service.get_chat_completion(task, params)

        node_map = {s.index: s for s in sections}
        
        for s in sections:
            s.children = [c for c in s.children if not isinstance(c, SectionNode)]

        roots = []
        for item in response["response"]:
            node = node_map.get(item["index"])
            if not node:
                continue

            if item["parent_index"] is None:
                roots.append(node)
            else:
                parent = node_map.get(item["parent_index"])        
                if parent:
                    parent.children.append(node)

        return roots

    def _build_section_skeleton(self, sections: List[SectionNode]):
        return [
            {
                "index": section.index,
                "title": section.title,
                "start_page": section.start_page,
            }
            for section in sections
        ]

    def _post_image_process(self, tree_section: List[SectionNode]):
        futures_map = []

        def traverse_and_submit(nodes):
            for node in nodes:
                if isinstance(node, SectionNode):
                    local_context = [
                        child.text for child in node.children 
                        if isinstance(child, TextLeaf) and child.text is not None
                    ]
                    
                    for child in node.children:
                        if isinstance(child, ImageLeaf):
                            logger.debug(f"Submitting caption task for image at {child.image_path}")
                            future = self._execute_captioning_task(child, node.title, local_context)
                            futures_map.append((future, child))
                        elif isinstance(child, SectionNode):
                            traverse_and_submit(child.children)

        traverse_and_submit(tree_section)
        
        if not futures_map:
            logger.info("No images found for captioning.")
            return

        logger.info(f"Processing {len(futures_map)} image captions...")
        for future, img_leaf in futures_map:
            try:
                res = future.result(timeout=120)
                img_leaf.text = res.get('description') or res.get('output') or "No description."
            except:
                img_leaf.text = "No description."
    
    def _execute_captioning_task(self, img_leaf: ImageLeaf, section_title: str, context: List[str]):
        full_path = os.path.join(config.base_dir, "static", img_leaf.image_path)
        image_data_url = pil_to_data_url(full_path)

        formatted_context = (
            f"Image in section: '{section_title}'.\n"
            f"Context: {' '.join(context)}\n"
        )
        
        params = {
            "question": "",
            "image_base64": image_data_url,
            "mime_type": "image/png",
            "context": formatted_context
        }
        return self.executor.submit(llm_service.get_chat_completion, "image_captioning", params)

    def _init_converter(self) -> DocumentConverter:        
        options = PdfPipelineOptions()
        options.generate_page_images = True
        options.generate_picture_images = True
        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
    
    def _init_splitter(self, chunk_size, chunk_overlap) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""]
        )
    

        
retrieve_service = RetrieveService(chunk_size=2000, chunk_overlap=200)