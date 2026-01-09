import os
import html
import json
import uuid
import base64
import pathlib
import logging
import textwrap
from typing import Optional, List, Dict, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

import graphviz
from PIL import ImageOps
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from core import config, openai_embeddings, latex_ocr
from utils.image_caption import pil_to_data_url
from services.srv_qdrant import qdrant_service
from services.srv_llm import llm_service

from pydantic import BaseModel, Field
class TextLeaf(BaseModel):
    index: Optional[int] = Field(0, description="Thứ tự của văn bản")
    text: str = Field(description="Nội dung văn bản")
    page: Optional[int] = Field(..., description="Số trang của văn bản")

class ImageLeaf(BaseModel):
    index: Optional[int] = Field(0, description="Thứ tự của hình ảnh")
    text: Optional[str] = Field(..., description="Caption của hình ảnh")
    page: Optional[int] = Field(..., description="Số trang của hình ảnh")
    image_path: str = Field(description="Đường dẫn tương đối đến hình ảnh")

class SectionNode(BaseModel):
    index: int = Field(0, description="Thứ tự của chương hoặc mục")
    title: str = Field(description="Tiêu đề của chương hoặc mục")
    level: int = Field(description="Cấp độ phân cấp (1 cho chương lớn, 2 cho mục con,...)")

    start_page: Optional[int] = Field(..., description="Trang bắt đầu")
    end_page: Optional[int] = Field(..., description="Trang kết thúc")

    children: List[Union["SectionNode", TextLeaf, ImageLeaf]] = Field(
        description="Danh sách các phần tử con của chương hoặc mục",
        default=[])

SectionNode.model_rebuild()

logger = logging.getLogger(__name__)

class RetrieveService:
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
            # Chuyển đổi PDF
            conversion_result = self.converter.convert(file_path)
            logger.info("PDF conversion completed successfully.")
            
            file_basename = pathlib.Path(file_path).stem
            image_save_dir = os.path.join(config.static_dir, f"{file_basename}_{source_id}")
            os.makedirs(image_save_dir, exist_ok=True)
            logger.info(f"Artifact directory created: {image_save_dir}")

            # 1. Trích xuất cấu trúc phẳng
            logger.info("\t1. Extracting flat structure from document items...")
            flat_sections = self._process_structure(conversion_result, image_save_dir)
            logger.info(f"Extracted {len(flat_sections)} flat sections.")
            
            # 2. LLM dựng cây phân cấp
            logger.info("\t2. Building hierarchical tree with LLM...")
            hierarchical_tree = self._build_section_hierarchical_tree(flat_sections)
            
            # 3. Post-process: End-page
            logger.info("\t3. Post-process: Cập nhật end_page cho các SectionNode...")
            hierarchical_tree = self._post_endpage_process(hierarchical_tree)

            # 4. Post-process: Title Contextual
            logger.info("\t4. Post-process: Cập nhật title context cho các SectionNode...")
            hierarchical_tree = self._post_section_title_context(hierarchical_tree)

            # 5. Post-process: Captioning ảnh song song
            logger.info("\t5. Post-process: Image captioning...")
            self._post_image_process(hierarchical_tree)
            
            # 5. # Vẽ và lưu sơ đồ cây vào thư mục artifact
            plot_path = os.path.join(image_save_dir, "document_structure")
            self._plot_tree(hierarchical_tree, plot_path)

            logger.info(f"Successfully processed file: {file_basename}")
            return hierarchical_tree

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            raise e

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
                        if isinstance(child, TextLeaf)
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
        return ImageLeaf(text=None, page=page, image_path=img_full_path)
    
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
        full_path = os.path.join(config.base_dir, img_leaf.image_path)
        
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