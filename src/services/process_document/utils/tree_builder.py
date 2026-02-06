from collections import deque
from typing import List, Dict, Any, Optional

from core import config, logger
from services.llm.srv_llm import llm_service
from .data_models import SectionNode

class TreeBuilder:
    def build(self, flat_nodes: List[SectionNode]) -> List[SectionNode]:
        logger.info("TreeBuilder: start building section tree")

        # Tiền xử lý cây bằng chuyển node text vào trong node header trên nó
        naive_tree = self._naive_build_tree(flat_nodes)

        # Thu thập roots của naive tree để LLM phân cấp
        root_nodes = [node for node in naive_tree if node.label == "header"]
        skeleton = [{"index": h.order_id, "title": h.content, "page": h.page} for h in root_nodes]

        task = "correct_section_structure"
        params = {"question": "", "sections": skeleton}
        llm_response = llm_service.get_chat_completion(task, params)["response"]

        # Map về cây hoàn chỉnh
        final_tree = self._llm_to_tree(llm_response, root_nodes)
        self.log_ascii_tree(final_tree)

        logger.info("TreeBuilder: tree built with %s nodes", len(final_tree))
        return final_tree

    def _llm_to_tree(self, llm_response: str, root_nodes: List[SectionNode]) -> List[SectionNode]:
        header_map = {h.order_id: h for h in root_nodes}
        roots: List[SectionNode] = []
        for item in llm_response:
            index = item.get("index")
            parent_index = item.get("parent_index")

            node = header_map.get(index)
            if node is None:
                logger.info("Header index %s not found", index)
                continue

            if parent_index is None:
                roots.append(node)
            else:
                parent = header_map.get(parent_index)
                if parent is None:
                    logger.info(
                        "Parent %s not found for header %s",
                        parent_index, index
                    )
                    roots.append(node)
                else:
                    node.parent_id = parent.order_id
                    parent.children.append(node)

        logger.info("TreeBuilder: built %d root headers", len(roots))
        return roots

    def _naive_build_tree(self, flat_nodes: List[SectionNode]) -> List[SectionNode]:
        roots = []
        current_header: SectionNode = None
        for node in flat_nodes:
            if node.label == "header":
                current_header = node
                roots.append(node)
            
            else:
                # Nếu chưa có header hiện tại --> roots
                if not current_header:
                    roots.append(node)

                # Nếu có header hiện tại --> append vào children header hiện tại
                else:
                    current_header.children.append(node)
                    node.parent_id = current_header.order_id
        logger.info("TreeBuilder: naive tree built with %s nodes", len(roots))
        return roots
    

    def log_ascii_tree(
        self,
        roots: List[SectionNode],
        *,
        show_page: bool = True,
        max_title_len: int = 50,
    ):
        def fmt_title(node: SectionNode) -> str:
            title = node.content or node.label
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