from core import logger
from services import llm_service
from .data_models import DocPageModel, SectionNode
from .image_caption import image_caption_service

class OcrService:
    def ocr_pages(self, pages: list[DocPageModel], file_path: str, filename: str) -> list[SectionNode]:
        logger.info(f"OCR: Starting parallel processing for {len(pages)} pages")
        
        # Step 1: Batch OCR all pages
        ocr_tasks = []
        for page in pages:
            task = "image_captioning_v2"
            params = {"images": [page.base64]}
            ocr_tasks.append((task, params))
        
        logger.info(f"OCR: Submitting {len(ocr_tasks)} OCR tasks")
        ocr_results = llm_service.batch_get_chat_completion(ocr_tasks)
        
        # Step 2: Collect all image captioning tasks
        image_caption_tasks = []
        image_metadata = []
        
        for page_idx, page in enumerate(pages):
            for img in page.images:
                task = "image_captioning"
                params = {"images": [img.base64, page.base64]}
                image_caption_tasks.append((task, params))
                image_metadata.append((page_idx, img))
        
        # Batch image captioning
        if image_caption_tasks:
            logger.info(f"OCR: Submitting {len(image_caption_tasks)} image captioning tasks")
            image_caption_results = llm_service.batch_get_chat_completion(image_caption_tasks)
        else:
            image_caption_results = []
        
        # Organize image captions by page for correct ordering
        image_captions_by_page = {}  # {page_idx: [(img_idx, caption, img), ...]}
        for cap_idx, (idx, caption_result, error) in enumerate(image_caption_results):
            page_idx, img = image_metadata[cap_idx]
            
            if page_idx not in image_captions_by_page:
                image_captions_by_page[page_idx] = []
            
            if error:
                logger.error(f"Image caption error for page {page_idx}: {error}")
                caption_text = ""
            else:
                caption_text = caption_result.get("description", "")
            
            image_captions_by_page[page_idx].append((cap_idx, caption_text, img))
        
        # Step 3: Build flat nodes - interleave text and images per page
        flat_nodes = []
        order_id = 0
        
        for page_idx, (idx, ocr_result, error) in enumerate(ocr_results):
            page = pages[page_idx]
            
            if error:
                logger.error(f"OCR error for page {page_idx}: {error}")
                continue
            
            page_segments = ocr_result.get("ocr_response", [])
            page_segments.sort(key=lambda x: x["index"])
            
            # Build text/header nodes for this page
            for i, segment in enumerate(page_segments):
                node = SectionNode(
                    file_path=file_path,
                    filename=filename,
                    order_id=order_id,
                    label="header" if segment.get("label") == "header" else "text",
                    content=segment.get("content"),
                    page=page.page_number,
                )
                flat_nodes.append(node)
                order_id += 1
            
            # Add image nodes for this page (right after text segments of this page)
            if page_idx in image_captions_by_page:
                for cap_idx, caption_text, img in image_captions_by_page[page_idx]:
                    image_node = SectionNode(
                        file_path=img.static_file_path,
                        filename=filename,
                        order_id=order_id,
                        label="image",
                        content=caption_text,
                        page=page.page_number,
                        image_path=img.static_file_path
                    )
                    flat_nodes.append(image_node)
                    order_id += 1
        
        logger.info(f"OCR: Completed processing, total nodes: {len(flat_nodes)}")
        return flat_nodes
            
    def ocr_page(self, page: DocPageModel):
        """Legacy method for single page OCR"""
        task = "image_captioning_v2"
        params = {"images": [page.base64]}
        response = llm_service.get_chat_completion(task, params)
        return response

ocr_service = OcrService()