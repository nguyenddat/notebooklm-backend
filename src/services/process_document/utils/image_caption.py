from typing import List

from services import llm_service
from .data_models import DocPageModel, SectionNode

class ImageCaptionService:
    def caption_images_from_pages(self, pages: List[DocPageModel]):
        results = []
        for x, page in enumerate(pages):
            base64_images = [img.base64 for img in page.images]
            captions = self.caption_images(base64_images, page.base64)            
            
            for y, (img, caption) in enumerate(zip(page.images, captions)):
                node = SectionNode(
                    order_id=x * 1000 + y,
                    label="image",
                    content=caption.get("description", ""),
                    file_path=img.static_file_path
                )
                results.append(node)
        return results
    
    def caption_images(self, base64_images: List[str], full_page_base64: str):
        captions = []
        for base64 in base64_images:
            caption_result = self.caption_image(base64, full_page_base64)
            captions.append(caption_result)
        return captions
    
    def caption_image(self, base64: str, full_page_base64: str):
        task = "image_captioning"
        params = {"images": [base64, full_page_base64]}
        result = llm_service.get_chat_completion(task, params)
        return result

image_caption_service = ImageCaptionService()