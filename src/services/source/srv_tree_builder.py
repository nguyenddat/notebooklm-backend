from typing import List, Dict, Any

from core import logger
from services.llm.srv_llm import llm_service
from services.source.data_models import SectionNode

class TreeBuilder:
    def __init__(self):
        pass
    
    def build(self, flat_sections: List[SectionNode]) -> List[SectionNode]:
        logger.info("TreeBuilder: start building section tree")
        headers = self.collect_headers(flat_sections)
        logger.info("Collected %d header sections", len(headers))
        
        skeleton = self.build_skeleton(headers)
        logger.debug("Skeleton sent to LLM: %s", skeleton)
        
        # Gọi LLM
        task = "correct_section_structure"
        params = {"question": "", "sections": skeleton}
        llm_response = llm_service.get_chat_completion(task, params)["response"]
        
        # Map về List sections
        header_roots = self.llm_to_headers(headers, llm_response)
        self.log_ascii_tree(header_roots)
        return header_roots
    
    def llm_to_headers(self, headers: List[SectionNode], llm_response: Any):
        header_map = self.build_header_map(headers)

        # reset children để tránh append trùng
        for h in headers:
            # h.children.clear()
            h.parent_id = None

        roots: List[SectionNode] = []

        for item in llm_response:
            index = item.get("index")
            parent_index = item.get("parent_index")

            node = header_map.get(index)
            if node is None:
                logger.warning("Header index %s not found", index)
                continue

            if parent_index is None:
                roots.append(node)
            else:
                parent = header_map.get(parent_index)
                if parent is None:
                    logger.warning(
                        "Parent %s not found for header %s",
                        parent_index, index
                    )
                    roots.append(node)
                else:
                    node.parent_id = parent.order_id
                    parent.children.append(node)

        logger.info("TreeBuilder: built %d root headers", len(roots))
        return roots
            
    def build_skeleton(self, headers: List[SectionNode]) -> List[dict]:
        return [
            {
                "index": h.order_id,
                "title": h.title,
                "page": h.page,
            }
            for h in headers
        ]
    
    def collect_headers(self, flat_sections: List[SectionNode]) -> List[SectionNode]:
        return [s for s in flat_sections if s.label == "header"]

    def build_header_map(self, headers: List[SectionNode]) -> Dict[int, SectionNode]:
        return {h.order_id: h for h in headers}


    def log_ascii_tree(
        self,
        roots: List[SectionNode],
        *,
        show_page: bool = True,
        max_title_len: int = 80,
    ):
        def fmt_title(node: SectionNode) -> str:
            title = node.title or node.label
            if len(title) > max_title_len:
                title = title[:max_title_len] + "…"

            meta = []
            if show_page and node.page is not None:
                meta.append(f"p{node.page}")
            meta.append(node.label or "node")

            return f"{title} [{' '.join(meta)}]"

        def _log(node: SectionNode, prefix: str, is_last: bool):
            branch = "└── " if is_last else "├── "
            logger.info("%s%s%s", prefix, branch, fmt_title(node))

            next_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(node.children):
                _log(child, next_prefix, i == len(node.children) - 1)

        logger.info("========== SECTION TREE ==========")

        for i, root in enumerate(roots):
            is_last_root = i == len(roots) - 1
            logger.info(fmt_title(root))
            for j, child in enumerate(root.children):
                _log(child, "", j == len(root.children) - 1)

        logger.info("======== END SECTION TREE ========")


tree_builder = TreeBuilder()