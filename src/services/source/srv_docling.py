import io
import os
import uuid
from pathlib import Path
from typing import Union, List, Any, Optional

from PIL import ImageOps

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.document import ConversionResult

from core import config, log, latex_ocr
from utils.hash import get_bytes_and_hash, normalize_text
from services.redis import redis_service, RedisKeys
from services.source.data_models import SectionNode

class DoclingService:
    def __init__(self):
        options = PdfPipelineOptions()
        options.generate_page_images = True
        options.generate_picture_images = True
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        
    def file_to_flat_sections(self, file: Union[bytes, str, Path]) -> List[SectionNode]:
        conversion_result = self.load_file(file)
        flat_sections = self.process_conversion_result(conversion_result)
        return flat_sections

    def load_file(self, file: Union[bytes, str, Path]) -> ConversionResult:
        file_bytes, file_hash = get_bytes_and_hash(file)
        cache_key = RedisKeys.doc_cache(file_hash)
        
        # Kiểm tra cache
        cached_result = redis_service.get_object(cache_key)
        if cached_result:
            log.info(f"Cache Hit: {file_hash[:10]}")
            return cached_result

        # Convert nếu chưa có cache
        log.info(f"Cache Miss: Đang xử lý {file_hash[:10]}...")
        source = io.BytesIO(file_bytes)        
        result = self.converter.convert(source, input_format=InputFormat.PDF)
        
        # 4. Lưu cache
        redis_service.set_object(cache_key, result)
        log.success(f"Đã lưu cache thành công")
        
        return result
    
    def process_conversion_result(self, result: ConversionResult) -> List[SectionNode]:
        sections: List[SectionNode] = []
        current_header: Optional[SectionNode] = None
        
        for i, (item, _) in enumerate(result.document.iterate_items()):
            prov = item.prov[0] if item.prov else None
            page = prov.page_no if prov else 1
            
            node = self.process_item(i, item, page, result)
            if node is None:
                continue
            
            # Nếu là header thì tạo header mới,
            if node.title == "header":
                if current_header:
                    sections.append(current_header)
                current_header = node
            else:
                if current_header:
                    node.parent_id = current_header.point_id
                    current_header.children.append(node)
                
                else:
                    sections.append(node)
            
            if current_header:
                sections.append(current_header)
        return sections
                        
    def process_item(self, index: int, item: Any, page: int, result: ConversionResult) -> SectionNode | None:
        label = item.__class__.__name__
        node = SectionNode(order_id=index, page=page, label=label)
        if label == "SectionHeaderItem":
            label = "header"
            node.label = label
            
            node.title = content
            node.content = content
            content = normalize_text(item.text)
            
            return node if content else None
        
        elif label == "TableItem":
            label = "table"
            node.label = label

            table_md = item.export_to_markdown()
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
            img_path = Path(config.image_save_dir) / filename
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
            log.warning(f"Chưa hỗ trợ xử lý item type: {label}")
            return None

docling_service = DoclingService()