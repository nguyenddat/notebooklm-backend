import os
import html
import textwrap
import logging
import graphviz
from typing import List

from utils.utils_docling.models import SectionNode, TextLeaf, ImageLeaf

logger = logging.getLogger(__name__)

def plot_tree(tree_roots: List[SectionNode], output_path: str):
    try:
        dot = graphviz.Digraph(comment='Document Structure', format='png')

        dot.attr(
            rankdir='TB',     # top -> bottom
            dpi='300',
            nodesep='0.4',
            ranksep='0.8',
            charset='UTF-8'
        )

        dot.attr('node', fontname='Arial', fontsize='12', margin='0.2')
        dot.attr('edge', arrowhead='vee', arrowsize='0.8')

        def wrap_text(text, width=30):
            return "\n".join(textwrap.wrap(text, width=width))

        def gv_escape(text: str) -> str:
            """Escape text an toàn cho Graphviz HTML label"""
            return html.escape(text, quote=False)

        def add_nodes(nodes, parent_id=None):
            for i, node in enumerate(nodes):
                node_id = f"{type(node).__name__}_{getattr(node, 'index', i)}_{id(node)}"

                # ===== SECTION NODE =====
                if isinstance(node, SectionNode):
                    wrapped_title = gv_escape(
                        wrap_text(node.title, width=40)
                    )

                    label = f"""<
    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
    <TR>
        <TD BGCOLOR="#ADD8E6"><B>SECTION</B></TD>
    </TR>
    <TR>
        <TD>{wrapped_title}</TD>
    </TR>
    <TR>
        <TD BGCOLOR="#F0F8FF">
        <I>Page {node.start_page}-{node.end_page}</I>
        </TD>
    </TR>
    </TABLE>
    >"""

                    dot.node(node_id, label=label, shape='none')
                    add_nodes(node.children, node_id)

                # ===== TEXT LEAF =====
                elif isinstance(node, TextLeaf):
                    clean_text = (
                        node.text
                        .replace('[Dữ liệu bảng]:', 'TABLE:')
                        .strip()
                    )

                    display_text = wrap_text(
                        clean_text[:60] + ("..." if len(clean_text) > 60 else ""),
                        width=25
                    )

                    safe_text = gv_escape(display_text)

                    label = f"TEXT (P{node.page})\n{safe_text}"
                    dot.node(
                        node_id,
                        label=label,
                        shape='note',
                        style='filled',
                        color='#FFFACD'
                    )

                # ===== IMAGE LEAF =====
                elif isinstance(node, ImageLeaf):
                    img_name = gv_escape(os.path.basename(node.image_path))
                    label = f"IMAGE (P{node.page})\n{img_name}"

                    dot.node(
                        node_id,
                        label=label,
                        shape='component',
                        style='filled',
                        color='#90EE90'
                    )

                if parent_id:
                    dot.edge(parent_id, node_id)

        add_nodes(tree_roots)

        render_path = dot.render(output_path, cleanup=True)
        logger.info(f"Tree plot rendered at: {render_path}")

    except Exception as e:
        logger.error(f"Could not plot tree: {str(e)}", exc_info=True)
        raise e
