import os, uuid
from PIL import ImageOps

from core import config
from core import latex_ocr
from utils.utils_docling.models import TextLeaf, ImageLeaf

def process_text_item(item, page: int):
    if not item.text:
        return None
    return TextLeaf(text=item.text.strip(), page=page)

def process_table_item(item, page, conversion_results):
    table_md = item.export_to_markdown(doc=conversion_results.document)
    return TextLeaf(
        text=f"[Table Data]:\n{table_md}",
        page=page
    )


def process_formula_item(item, page, conversion_results):
    page_obj = conversion_results.pages[page - 1]
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

    latex = latex_ocr(formula_img)
    return TextLeaf(text=f"$$ {latex} $$", page=page) if latex else None

def process_picture_item(item, page, conversion_results, image_save_dir):
    img = item.get_image(conversion_results)
    if not img or img.size[0] * img.size[1] < config.min_image_area:
        return None

    filename = f"img_p{page}_{uuid.uuid4().hex[:8]}.png"
    full_path = os.path.join(image_save_dir, filename)
    img.save(full_path)

    rel_path = os.path.relpath(full_path, start=config.static_dir)
    return ImageLeaf(
        text=None,
        page=page,
        image_path=rel_path.replace(os.sep, "/")
    )
