from utils.utils_docling.models import SectionNode, TextLeaf, ImageLeaf
from utils.utils_docling.items import process_text_item, process_table_item, process_formula_item, process_picture_item

def process_structure(conversion_results, image_save_dir):
    sections = []
    current_section = None

    for i, (item, _) in enumerate(conversion_results.document.iterate_items()):
        label = item.__class__.__name__
        prov = item.prov[0] if item.prov else None
        page = prov.page_no if prov else 1

        if label == "SectionHeaderItem":
            current_section = SectionNode(
                index=i,
                title=item.text.strip(),
                level=getattr(item, "level", 1),
                start_page=page,
                end_page=None,
                children=[]
            )
            sections.append(current_section)
            continue

        if not current_section:
            continue

        leaf = None
        if label == "TextItem":
            leaf = process_text_item(item, page)
        elif label == "TableItem":
            leaf = process_table_item(item, page, conversion_results)
        elif label == "FormulaItem":
            leaf = process_formula_item(item, page, conversion_results)
        elif label == "PictureItem":
            leaf = process_picture_item(item, page, conversion_results, image_save_dir)

        if leaf:
            leaf.index = i
            current_section.children.append(leaf)

    return sections