import os
import html
import math
import json
import uuid
import base64
import pathlib
import logging
import textwrap
from typing import Optional, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

import graphviz
from PIL import ImageOps
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core import config, openai_embeddings, latex_ocr
from utils.image_caption import pil_to_data_url
from services.srv_qdrant import qdrant_service
from services.srv_llm import llm_service

from pydantic import BaseModel, Field, TypeAdapter

class TextLeaf(BaseModel):
    index: int = Field(0, description="Thứ tự của văn bản")
    text: Optional[str] = Field(..., description="Nội dung văn bản")
    page: int = Field(..., description="Số trang của văn bản")

class ImageLeaf(TextLeaf):
    image_path: str = Field(description="Đường dẫn tương đối đến hình ảnh")

class SectionNode(BaseModel):
    index: int = Field(0, description="Thứ tự của chương hoặc mục")
    title: str = Field(description="Tiêu đề của chương hoặc mục")
    level: int = Field(description="Cấp độ phân cấp (1 cho chương lớn, 2 cho mục con,...)")

    start_page: Optional[int] = Field(..., description="Trang bắt đầu")
    end_page: Optional[int] = Field(..., description="Trang kết thúc")

    children: List[Union["SectionNode", TextLeaf, ImageLeaf]] = Field(
        description="Danh sách các phần tử con của chương hoặc mục",
        default=[]
    )

SectionNode.model_rebuild()

logger = logging.getLogger(__name__)

class RetrieveService:
    MAX_CONTEXT_CHARS = 2500
    BOOST_WEIGHT = 0.4
    EMBED_BATCH = 64
    MIN_IMAGE_AREA = 500

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.converter = self._init_converter()
        self.splitter = self._init_splitter(chunk_size, chunk_overlap)
        logger.info(f"Initialized RetrieveService with chunk_size={chunk_size}")


    def process_file(self, source_id: int, file_path: str, notebook_id: Optional[int] = None):
        logger.info(f"Starting processing file: {file_path} (source_id: {source_id})")
        try:
            conversion_result = self.converter.convert(file_path)
            logger.info("PDF conversion completed successfully.")
            
            file_basename = pathlib.Path(file_path).stem
            image_save_dir = os.path.join(config.static_dir, f"{file_basename}_{source_id}")
            os.makedirs(image_save_dir, exist_ok=True)
            logger.info(f"Artifact directory created: {image_save_dir}")

            logger.info("\t1. Extracting flat structure from document items...")
            flat_sections = self._process_structure(conversion_result, image_save_dir)
            logger.info(f"Extracted {len(flat_sections)} flat sections.")
            
            logger.info("\t2. Building hierarchical tree with LLM...")
            hierarchical_tree = self._build_section_hierarchical_tree(flat_sections)
            
            logger.info("\t3. Post-process: Cập nhật end_page cho các SectionNode...")
            hierarchical_tree = self._post_endpage_process(hierarchical_tree)

            logger.info("\t4. Post-process: Cập nhật title context cho các SectionNode...")
            hierarchical_tree = self._post_section_title_context(hierarchical_tree)

            logger.info("\t5. Post-process: Image captioning...")
            self._post_image_process(hierarchical_tree)

            logger.info(f"Successfully processed file: {file_basename}")
            return hierarchical_tree

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            raise e
        
    def retrieve(self, query: str, source_id: int, top_k: int = 5):
        query_vector = openai_embeddings.embed_query(query)

        text_hits = qdrant_service.search(
            query_embedding=query_vector,
            top_k=top_k * 2,
            doc_ids=[str(source_id)],
            types=["text"],
        )

        image_hits = qdrant_service.search(
            query_embedding=query_vector,
            top_k=top_k,
            doc_ids=[str(source_id)],
            types=["image"],
        )

        texts = []
        images = []

        for hit in text_hits:
            payload = hit["payload"]
            texts.append(payload["text"])

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

        ordered_nodes = self._collect_ordered_text(tree)
        if not ordered_nodes:
            return {"status": "empty", "points": 0}

        all_chunks = []

        # INDEX TEXT CHUNKS
        text_items = [n for n in ordered_nodes if n["type"] == "text"]

        if text_items:
            full_doc = self._build_long_document(text_items)
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

    def _collect_ordered_text(self, tree: List[SectionNode]) -> List[dict]:
        collected = []

        def traverse(nodes: List[Union[SectionNode, TextLeaf, ImageLeaf]], path_titles=[]):
            for node in nodes:
                if isinstance(node, SectionNode):
                    raw_title = getattr(node, "_raw_title", node.title)
                    traverse(node.children, path_titles + [raw_title])

                elif isinstance(node, (TextLeaf, ImageLeaf)):
                    if not node.text or len(node.text.strip()) < 5:
                        continue

                    collected.append({
                        "index": node.index,
                        "page": node.page,
                        "text": node.text,
                        "breadcrumb": " > ".join(path_titles),
                        "type": "image" if isinstance(node, ImageLeaf) else "text",
                        "image_path": getattr(node, "image_path", None)
                    })

        traverse(tree)
        return sorted(collected, key=lambda x: x["index"])

    def _build_long_document(self, ordered_nodes: List[dict]) -> str:
        parts = []
        for item in ordered_nodes:
            prefix = f"[Page {item['page']}]"
            if item["breadcrumb"]:
                prefix += f" {item['breadcrumb']}:"

            parts.append(f"{prefix}\n{item['text']}")
        return "\n\n".join(parts)

    def _pydantic_to_dict(self, hierarchical_tree):
        adapter = TypeAdapter(List[SectionNode])
        tree_data = adapter.dump_python(hierarchical_tree)
        return tree_data
    
    def _dict_to_pydantic(self, tree_data):
        adapter = TypeAdapter(List[SectionNode])
        tree = adapter.validate_python(tree_data)
        return tree

    def _process_structure(self, conversion_results, image_save_dir):
        sections = []
        current_section = None
        
        for i, (item, _) in enumerate(conversion_results.document.iterate_items()):
            label = item.__class__.__name__
            prov = item.prov[0] if item.prov else None
            page_no = prov.page_no if prov else 1

            if label == "SectionHeaderItem":
                current_section = SectionNode(
                    index=i,
                    title=item.text.strip(),
                    level=getattr(item, 'level', 1),
                    start_page=page_no,
                    end_page=None,
                    children=[]
                )
                sections.append(current_section)
                continue

            if not current_section:
                continue

            leaf = None
            if label == "TextItem" and item.text:
                leaf = self._process_docling_text_item(item, page_no)
            elif label == "TableItem":
                leaf = self._process_docling_table_item(item, page_no, conversion_results)
            elif label == "FormulaItem":
                leaf = self._process_docling_formula_item(item, page_no, conversion_results)
            elif label == "PictureItem":
                leaf = self._process_docling_picture_item(item, page_no, conversion_results, image_save_dir)

            if leaf:
                leaf.index = i
                current_section.children.append(leaf)

        return sections

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

    def _post_section_title_context(self, tree_sections: List[SectionNode], sep: str = " › "):
        def dfs(node: SectionNode, parent_titles: List[str]):
            if not hasattr(node, "_raw_title"):
                node._raw_title = node.title

            if parent_titles:
                node.title = sep.join(parent_titles + [node._raw_title])

            # DFS xuống con
            for child in node.children:
                if isinstance(child, SectionNode):
                    dfs(child, parent_titles + [node._raw_title])

        for root in tree_sections:
            dfs(root, [])
        return tree_sections

    
    def _post_endpage_process(self, tree_section: List[SectionNode]):
        def compute_end_page(node: SectionNode) -> Optional[int]:
            max_page = node.start_page

            for child in node.children:
                if isinstance(child, SectionNode):
                    child_end = compute_end_page(child)
                    if child_end is not None:
                        max_page = max(max_page, child_end)

                elif isinstance(child, (TextLeaf, ImageLeaf)):
                    if child.page is not None:
                        max_page = max(max_page, child.page)

            node.end_page = max_page
            return max_page

        for root in tree_section:
            compute_end_page(root)
        return tree_section
            

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
                            traverse_and_submit([child])

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
    
    def _calculate_parent_boost(self, query: str, parent_titles: List[str]) -> float:
        if not parent_titles:
            return 0.0
        
        full_path_context = " ".join(parent_titles).lower()
        query_words = set(query.lower().split())
        
        overlap = sum(1 for word in query_words if word in full_path_context)
        return min(overlap / max(len(query_words), 1), 1.0)

    def _get_recursive_text(self, node: Union[SectionNode, TextLeaf, ImageLeaf]) -> str:
        if isinstance(node, TextLeaf):
            return node.text if node.text else ""
        if isinstance(node, ImageLeaf):
            return f"\n[Hình ảnh (Trang {node.page}): {node.text or 'Mô tả không khả dụng'}]\n"
        
        res = [f"## {node.title}"]
        for child in node.children:
            res.append(self._get_recursive_text(child))
        return "\n".join(res)

    def _expand_context_recursively(self, path: List[SectionNode]) -> SectionNode:
        current_best = path[-1]
        
        for node in reversed(path):
            content_len = len(self._get_recursive_text(node))
            if content_len < self.MAX_CONTEXT_CHARS:
                current_best = node
            else:
                break
        return current_best

    def _find_path_to_index(self, tree: List[SectionNode], target_index: int) -> Optional[List[SectionNode]]:
        for node in tree:
            if node.index == target_index:
                return [node]
            
            for child in node.children:
                if isinstance(child, SectionNode):
                    res = self._find_path_to_index([child], target_index)
                    if res:
                        return [node] + res
                elif child.index == target_index:
                    return [node]
        return None

    def _process_docling_text_item(self, item, page):
        return TextLeaf(text=item.text.strip(), page=page)
    
    def _process_docling_table_item(self, item, page, conversion_results):
        table_md = item.export_to_markdown(doc=conversion_results.document)
        return TextLeaf(text=f"[Table Data]:\n{table_md}", page=page)
    
    def _process_docling_formula_item(self, item, page, conversion_results):
        latex = self._process_formula(item, page, conversion_results)
        return TextLeaf(text=f"$$ {latex} $$", page=page) if latex else None
    
    def _process_docling_picture_item(self, item, page, conversion_results, image_save_dir):
        img = item.get_image(conversion_results)
        if not img or (img.size[0] * img.size[1]) < self.MIN_IMAGE_AREA:
            return None
        
        img_filename = f"img_p{page}_{uuid.uuid4().hex[:8]}.png"
        img_full_path = os.path.join(image_save_dir, img_filename) 
        img.save(img_full_path)

        relative_path = os.path.relpath(
            img_full_path,
            start=config.static_dir
        )
        return ImageLeaf(text=None, page=page, image_path=relative_path.replace(os.sep, "/"))
    
    def _process_formula(self, item, page, conversion_results) -> str:
        page_obj = conversion_results.pages[page - 1]
        page_img = page_obj.get_image()
        
        prov = item.prov[0]
        bbox = prov.bbox
        if (abs(bbox.r - bbox.l) * abs(bbox.t - bbox.b)) < self.MIN_IMAGE_AREA: 
            return ""
        
        crop_box = (int(bbox.l), int(page_img.size[1] - bbox.t), int(bbox.r), int(page_img.size[1] - bbox.b))
        formula_img = ImageOps.expand(page_img.crop(crop_box), border=10, fill="white")
        return latex_ocr(formula_img)
    
    def _execute_captioning_task(self, img_leaf: ImageLeaf, section_title: str, context: List[str]):
        full_path = os.path.join(config.base_dir, "static", img_leaf.image_path)
        
        fmt = "png"
        mime_type = f"image/{fmt}"
        try:
            with open(full_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                img_b64 = f"data:image/{fmt.lower()};base64,{img_b64}"
        except Exception as e:
            logger.error(f"Could not read image file {full_path}: {e}")
            raise e

        formatted_context = (
            f"Image in section: '{section_title}'.\n"
            f"Context: {' '.join(context)[:200]}\n"
        )
        
        params = {
            "question": "",
            "image_base64": img_b64,
            "mime_type": mime_type,
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
    
    def _plot_tree(self, tree_roots: List[SectionNode], output_path: str):
        try:
            dot = graphviz.Digraph(comment='Document Structure', format='png')

            dot.attr(
                rankdir='TB',     # top -> bottom
                dpi='300',
                nodesep='0.4',
                ranksep='0.8',
                charset='UTF-8'
            )

            dot.attr('node', fontname='Arial', fontsize='12', margin='0.2')
            dot.attr('edge', arrowhead='vee', arrowsize='0.8')

            def wrap_text(text, width=30):
                return "\n".join(textwrap.wrap(text, width=width))

            def gv_escape(text: str) -> str:
                """Escape text an toàn cho Graphviz HTML label"""
                return html.escape(text, quote=False)

            def add_nodes(nodes, parent_id=None):
                for i, node in enumerate(nodes):
                    node_id = f"{type(node).__name__}_{getattr(node, 'index', i)}_{id(node)}"

                    # ===== SECTION NODE =====
                    if isinstance(node, SectionNode):
                        wrapped_title = gv_escape(
                            wrap_text(node.title, width=40)
                        )

                        label = f"""<
    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
    <TR>
        <TD BGCOLOR="#ADD8E6"><B>SECTION</B></TD>
    </TR>
    <TR>
        <TD>{wrapped_title}</TD>
    </TR>
    <TR>
        <TD BGCOLOR="#F0F8FF">
        <I>Page {node.start_page}-{node.end_page}</I>
        </TD>
    </TR>
    </TABLE>
    >"""

                        dot.node(node_id, label=label, shape='none')
                        add_nodes(node.children, node_id)

                    # ===== TEXT LEAF =====
                    elif isinstance(node, TextLeaf):
                        clean_text = (
                            node.text
                            .replace('[Dữ liệu bảng]:', 'TABLE:')
                            .strip()
                        )

                        display_text = wrap_text(
                            clean_text[:60] + ("..." if len(clean_text) > 60 else ""),
                            width=25
                        )

                        safe_text = gv_escape(display_text)

                        label = f"TEXT (P{node.page})\n{safe_text}"
                        dot.node(
                            node_id,
                            label=label,
                            shape='note',
                            style='filled',
                            color='#FFFACD'
                        )

                    # ===== IMAGE LEAF =====
                    elif isinstance(node, ImageLeaf):
                        img_name = gv_escape(os.path.basename(node.image_path))
                        label = f"IMAGE (P{node.page})\n{img_name}"

                        dot.node(
                            node_id,
                            label=label,
                            shape='component',
                            style='filled',
                            color='#90EE90'
                        )

                    if parent_id:
                        dot.edge(parent_id, node_id)

            add_nodes(tree_roots)

            render_path = dot.render(output_path, cleanup=True)
            logger.info(f"Tree plot rendered at: {render_path}")

        except Exception as e:
            logger.error(f"Could not plot tree: {str(e)}", exc_info=True)
            raise e
        
retrieve_service = RetrieveService(chunk_size=2000, chunk_overlap=200)