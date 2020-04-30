"""Make PNG AST graphs"""

import logging
import lark
from .load import file_parser
from .read import ReadLiterals

LOG = logging.getLogger(__name__)


def make_ast(filename, function, dest_png):
    with open(filename) as f:
        content = f.read()

    parser = file_parser()
    tree = parser.parse(content)
    ast = ReadLiterals().transform(tree)

    LOG.info(f"Creating PNG for function `{function}` in {filename}")

    for c in ast.children:
        if c.data == "def_" and c.children[0] == function:
            LOG.info(f"-> {dest_png}")
            lark.tree.pydot__tree_to_png(c, dest_png)
            return

    raise ValueError(f"Could not find function `{function}`.")
