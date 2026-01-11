from typing import List, Union
from utils.utils_docling.models import SectionNode, TextLeaf, ImageLeaf

def collect_ordered_text(tree: List[SectionNode]) -> List[dict]:
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

def build_long_document(ordered_nodes: List[dict]) -> str:
    parts = []
    for item in ordered_nodes:
        prefix = f"[Page {item['page']}]"
        if item["breadcrumb"]:
            prefix += f" {item['breadcrumb']}:"

        parts.append(f"{prefix}\n{item['text']}")
    return "\n\n".join(parts)
