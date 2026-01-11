from typing import List
from pydantic import TypeAdapter

from .utils_docling.models import SectionNode

def pydantic_tree_to_dict(tree: List[SectionNode]) -> list:
    adapter = TypeAdapter(List[SectionNode])
    return adapter.dump_python(tree)


def dict_to_pydantic_tree(tree_data: list) -> List[SectionNode]:
    adapter = TypeAdapter(List[SectionNode])
    return adapter.validate_python(tree_data)
