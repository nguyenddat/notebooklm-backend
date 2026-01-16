from typing import List, Iterable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import logger, config
from utils.image_caption import image_path_to_data_url
from services.source.data_models import SectionNode
from services.redis import redis_service, RedisKeys
from services.llm.srv_llm import llm_service

class ImageCaptionService:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        
    def process(self, roots: List[SectionNode]) -> None:
        linear_nodes = self.flatten_bfs(roots)
        image_nodes = [(i, n) for i, n in enumerate(linear_nodes) if n.is_image()]
        if not image_nodes:
            logger.info("ImageCaption: no image nodes found")
            return
        
        logger.info("ImageCaption: processing %d images", len(image_nodes))
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_single, idx, node, linear_nodes): node
                for idx, node in image_nodes
            }
        
            for future in as_completed(futures):
                node = futures[future]
                try:
                    caption = future.result()
                    if caption:
                        node.caption = caption
                        node.content = f"{caption}\n [Đường dẫn]({node.image_path})"
                except Exception as e:
                    logger.error("ImageCaption error for %s: %s", node.image_path, e)
    
    def flatten_bfs(self, roots: Iterable[SectionNode]) -> List[SectionNode]:
        result = []
        def dfs(node):
            result.append(node)
            for c in node.children:
                dfs(c)

        for r in roots:
            dfs(r)

        return result    

    def _get_adjacent_text(
        self,
        linear_nodes: List[SectionNode],
        index: int,
    ) -> tuple[str | None, str | None]:

        prev_text = None
        next_text = None

        # tìm node text trước
        for i in range(index - 1, -1, -1):
            n = linear_nodes[i]
            if n.is_text():
                prev_text = n.content.strip()
                break

        # tìm node text sau
        for i in range(index + 1, len(linear_nodes)):
            n = linear_nodes[i]
            if n.is_text():
                next_text = n.content.strip()
                break

        return prev_text, next_text
    
    def _process_single(self, index: int, node: SectionNode, flat_sections: List[SectionNode]) -> str | None:
        if not node.image_path:
            return None

        img_path = Path(config.static_dir) / node.image_path
        if not img_path.exists():
            logger.warning("Image not found: %s", img_path)
            return None

        # cache key
        image_bytes = img_path.read_bytes()
        image_hash = hash(image_bytes)
        cache_key = RedisKeys.image_caption(str(image_hash))

        cached = redis_service.get_object(cache_key)
        if cached:
            logger.debug("Image caption cache hit")
            return cached

        prev_text, next_text = self._get_adjacent_text(flat_sections, index)
        caption = self._caption_image(
            img_path,
            prev_text=prev_text,
            next_text=next_text,
        )

        if caption:
            redis_service.set_object(cache_key, caption)

        return caption
    
    def _caption_image(self, img_path: Path, *, prev_text: str | None, next_text: str | None) -> str:
        prompt_parts = ["Use the surrounding text as context: "]
        if prev_text:
            prompt_parts.append(f"Previous text:\n{prev_text}")

        if next_text:
            prompt_parts.append(f"Next text:\n{next_text}")

        task = "image_captioning"
        params = {
            "question": "\n".join(prompt_parts),
            "image_base64": image_path_to_data_url(img_path),
        }

        result = llm_service.get_chat_completion(task, params)
        return result["description"]
    
image_caption_service = ImageCaptionService()