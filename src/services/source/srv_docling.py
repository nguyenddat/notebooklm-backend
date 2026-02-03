import os
import uuid
import tempfile
from pathlib import Path
from typing import Union, List, Any, Optional

from PIL import ImageOps

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.document import ConversionResult

from core import config, logger, latex_ocr
from utils.hash import normalize_text
from services.source.data_models import SectionNode

class DoclingService:
    def __init__(self):
        options = PdfPipelineOptions()
        options.generate_page_images = True
        options.generate_picture_images = True
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        
    def file_to_flat_sections(self, file: Union[str, Path]) -> List[SectionNode]:
        conversion_result = self.load_file(file)
        
        image_dir = Path(config.static_dir) / file.stem
        image_dir.mkdir(parents=True, exist_ok=True)
        
        flat_sections = self.process_conversion_result(conversion_result, image_dir, file)        
        return flat_sections

    def load_file(self, file: Union[bytes, str, Path]) -> ConversionResult:
        result = self.converter.convert(file)
        return result
    
    def process_conversion_result(self, result: ConversionResult, image_save_dir: Union[str, Path], file_path: Union[str, Path]) -> List[SectionNode]:
        sections: List[SectionNode] = []
        current_header: Optional[SectionNode] = None
        
        for i, (item, _) in enumerate(result.document.iterate_items()):
            prov = item.prov[0] if item.prov else None
            page = prov.page_no if prov else 1
            
            node = self.process_item(i, item, page, result, image_save_dir, file_path)
            if node is None:
                continue
            
            # Nếu là header thì tạo header mới
            if node.label == "header":
                if current_header:
                    sections.append(current_header)
                current_header = node
            else:
                if current_header:
                    node.parent_id = current_header.order_id
                    current_header.children.append(node)
                
                else:
                    sections.append(node)
        
        if current_header:
            sections.append(current_header)               
        return sections
                        
    def process_item(self, index: int, item: Any, page: int, result: ConversionResult, image_save_dir: Union[str, Path], file_path: Union[str, Path]) -> SectionNode | None:
        label = item.__class__.__name__
        filename = Path(file_path).name
        # Remove /app/static prefix if present to keep path relative
        clean_path = str(file_path).replace("/app/static/", "")
        if clean_path.startswith("/"):
             clean_path = clean_path.lstrip("/")
             
        node = SectionNode(order_id=index, page=page, label=label, file_path=clean_path, filename=filename)
        if label == "SectionHeaderItem":
            label = "header"
            node.label = label
            
            content = normalize_text(item.text)
            if not content:
                return None
            
            node.title = content
            node.content = content
            return node

        elif label == "TextItem":
            label = "text"
            node.label = label
            
            content = normalize_text(item.text)
            if not content:
                return None
            
            node.content = content
            return node
        
        elif label == "TableItem":
            label = "table"
            node.label = label

            table_md = item.export_to_markdown(doc=result.document)
            if not table_md:
                return None
            
            node.content = table_md
            return node if table_md else None
        
        elif label == "FormulaItem":
            page_obj = result.pages[page - 1]
            page_img = page_obj.get_image()

            prov = item.prov[0]
            bbox = prov.bbox
            if abs(bbox.r - bbox.l) * abs(bbox.t - bbox.b) < config.min_image_area:
                return None

            crop_box = (
                int(bbox.l),
                int(page_img.size[1] - bbox.t),
                int(bbox.r),
                int(page_img.size[1] - bbox.b),
            )

            formula_img = ImageOps.expand(
                page_img.crop(crop_box),
                border=10,
                fill="white"
            )
            label = "formula"
            node.label = label
            
            latex = latex_ocr(formula_img)
            node.content = f"$$ {latex} $$"
            return node if latex else None

        elif label == "PictureItem":
            img = item.get_image(result)
            if not img or img.size[0] * img.size[1] < config.min_image_area:
                return None
            
            filename = f"img_p{page}_{uuid.uuid4().hex[:8]}.png"
            img_path = Path(image_save_dir) / filename
            img.save(img_path)

            label = "image"
            node.label = label
            
            rel_path = os.path.relpath(img_path, start=config.static_dir)
            node.image_path = str(rel_path)
            return node
        
        elif label == "ListItem":
            label = "list"
            node.label = label
            
            text = item.text.strip() if item.text else ""
            marker = getattr(item, "marker", "-")
            node.content = f"{marker} {normalize_text(text)}"
            return node if text else None

        else:
            logger.warning(f"Chưa hỗ trợ xử lý item type: {label}")
            return None

docling_service = DoclingService()