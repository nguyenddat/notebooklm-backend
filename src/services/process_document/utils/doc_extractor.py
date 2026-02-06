import os
import base64
import subprocess
from typing import List

import fitz
from pydantic import BaseModel, Field

from core import config, logger
from .data_models import DocImageModel, DocPageModel

class DocExtractor:
    def __init__(self):
        self.min_width = config.min_width
        self.min_height = config.min_height
        self.max_width = config.max_width
        self.max_height = config.max_height
    
    def convert_pdf_to_pages(self, pdf_path: str, output_dir: str) -> List[DocPageModel]:
        doc = fitz.open(pdf_path)
        os.makedirs(output_dir, exist_ok=True)
        
        results: List[DocPageModel] = []
        for page_index in range(len(doc)):
            page = doc[page_index]

            # Tạo ảnh toàn trang
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            page_bytes = pix.tobytes("png")
            page_base64 = base64.b64encode(page_bytes).decode('utf-8')
            
            # Lấy danh sách hình ảnh trong trang
            image_list = page.get_images(full=True)
            doc_page = DocPageModel(page_number=page_index + 1, base64=page_base64, images=[], mime_type="image/png")
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                
                # Nếu w, h không hợp lệ thì bỏ qua
                width = base_image["width"]
                height = base_image["height"]
                if not self.check_is_valid_size(width, height):
                    continue
                
                # Tạo object hình ảnh
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                image_path = os.path.join(output_dir, f"image_p{page_index+1}_{img_index+1}.{image_ext}")
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                doc_image = DocImageModel(
                    static_file_path=image_path.replace("\\", "/").replace("app/static/", ""),
                    base64=image_base64,
                    caption=None,
                    mime_type=image_ext,
                )
                
                # Thêm vào trang
                doc_page.images.append(doc_image)
                
            results.append(doc_page)
        doc.close()
        return results
    
    def convert_docx_to_pdf(self, docx_path: str) -> str:
        temp_pdf = docx_path.replace(".docx", ".pdf")
        try:
            subprocess.run([
                'libreoffice', '--headless', '--convert-to', 'pdf', 
                docx_path, '--outdir', os.path.dirname(docx_path)
            ], check=True, capture_output=True)
            return temp_pdf

        except subprocess.CalledProcessError as e:
            logger.info(f"Error converting DOCX to PDF: {e.stderr.decode()}")
    
    def check_is_valid_size(self, width: int, height: int) -> bool:
        if width < self.min_width or height < self.min_height:
            return False
        if width > self.max_width or height > self.max_height:
            return False
        return True

doc_extractor = DocExtractor()