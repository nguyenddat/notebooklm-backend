from utils.utils_docling.models import SectionNode, TextLeaf, ImageLeaf

def post_endpage(tree):
    def dfs(node):
        max_page = node.start_page
        for c in node.children:
            if isinstance(c, SectionNode):
                max_page = max(max_page, dfs(c))
            elif isinstance(c, (TextLeaf, ImageLeaf)):
                max_page = max(max_page, c.page)
        node.end_page = max_page
        return max_page

    for root in tree:
        dfs(root)
    return tree


def post_title_context(tree, sep=" › "):
    def dfs(node, parents):
        node._raw_title = getattr(node, "_raw_title", node.title)
        if parents:
            node.title = sep.join(parents + [node._raw_title])
        for c in node.children:
            if isinstance(c, SectionNode):
                dfs(c, parents + [node._raw_title])

    for root in tree:
        dfs(root, [])
    return tree
