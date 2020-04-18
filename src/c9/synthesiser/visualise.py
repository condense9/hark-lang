"""Make a DAG visualisation

Essential for Step Function replacement.
"""

from collections import deque
import logging

from ..lang import *
from graphviz import Digraph, Graph
from ..compiler.compiler_utils import traverse_dag, traverse_fn

C_RED = "red"
C_GREEN = "green"
C_CYAN = "#e0ffff"


START_STYLE = dict(style="filled", color="orange")
CHOICE_STYLE = dict(shape="diamond")
TASK_STYLE = dict(shape="rectangle")
FOREIGN_STYLE = dict(color=C_CYAN, style="filled", shape="rectangle")
THEN_STYLE = dict(label="True", color=C_GREEN)
ELSE_STYLE = dict(label="False", color=C_RED)


def label(node):
    if isinstance(node, Func):
        return f"{node.name}: {node.__name__}"
    elif isinstance(node, ForeignCall):
        return f"{node.name}: {node.function.__name__}"
    elif isinstance(node, Funcall):
        return f"{node.name}: {node.function_name}"
    elif isinstance(node, If):
        return f"{node.name}: If {node.cond}"
    elif isinstance(node, Quote):
        return f"{node.unquote()}"
    elif isinstance(node, Symbol):
        return f"{node.name}: Symbol {node.symbol_name}"
    else:
        return str(node)


def get_node_label_and_style(n):
    if isinstance(n, Funcall):
        style = TASK_STYLE
        if isinstance(n.function, Foreign):
            _label = f"{n.function_name}"
            style = FOREIGN_STYLE
        elif isinstance(n.function, Func):
            _label = n.function_name
        else:
            _label = f"Funcall *{n.function_name}"

    elif isinstance(n, Symbol):
        _label = n.symbol_name
        style = START_STYLE

    elif isinstance(n, If):
        _label = "If"
        style = CHOICE_STYLE

    else:
        _label = label(n)
        style = TASK_STYLE

    return _label, style


def add_dependencies(graph, existing, n):
    item = existing[n]
    if isinstance(n, If):
        cond_item = build_tree(graph, n.cond, existing)
        then_item = build_tree(graph, n.then, existing)
        else_item = build_tree(graph, n.els, existing)
        cond_link = graph.edge(cond_item, item)
        then_link = graph.edge(item, then_item, **THEN_STYLE)
        else_link = graph.edge(item, else_item, **ELSE_STYLE)

    elif isinstance(n, Funcall):
        for o in n.operands[1:]:
            operand_item = build_tree(graph, o, existing)
            graph.edge(operand_item, item)

    else:
        for o in n.operands:
            operand_item = build_tree(graph, o, existing)
            graph.edge(operand_item, item)


def build_tree(graph, n, existing):
    """build the tree recursively"""
    logging.info("Building graph from Node: %s", n)

    if n in existing:
        return existing[n]

    # First add the node itself
    label, style = get_node_label_and_style(n)
    graph.node(n.name, label, **style)
    existing[n] = n.name

    # Then add the dependencies
    add_dependencies(graph, existing, n)

    # And return the item so it can be referenced later
    return n.name


def build_fn_graph(graph, fn):
    # so confusing. fn.name is the Node name, fn.__name__ is the function name
    placeholders = fn.placeholders
    node = fn.b_reduce(placeholders)
    existing = {}

    sub = Digraph()
    sub.attr(rank="min")
    for p in placeholders:
        label, style = get_node_label_and_style(p)
        sub.node(p.name, label, **style)
        existing[p] = p.name
    graph.subgraph(sub)

    sub = Digraph()
    build_tree(sub, node, existing)
    graph.subgraph(sub)
    return graph


def make_complete_graph(root_fn, include_legend=True):
    # if include_legend:
    #     graph = GvGen("Legend")
    #     graph.legendAppend(TASK_STYLE, "A C9 Function")
    #     graph.legendAppend(FOREIGN_STYLE, "A Foreign function call")
    # else:
    #     graph = GvGen()

    graph = Digraph(comment=f"Graph for {root_fn.name}")

    for fn in traverse_dag(root_fn, only=Func):
        if not isinstance(fn, Foreign):
            sub = Digraph(name=f"cluster_{fn.name}")
            sub.attr("graph", label=fn.__name__)
            build_fn_graph(sub, fn)
            graph.subgraph(sub)

    return graph


###
#
# Irreducible:
# - Quote
# - Symbol
# - Func (it's a Quote)
# - Foreign (same)
#
# Reducible:
# - If
# - Do
# - Funcall (either reduces to a Func or a Symbol, and has arguments)
# - ForeignCall (it has arguments)
# - Asm

if __name__ == "__main__":

    @Foreign
    def foo(x):
        pass

    @Foreign
    def foo2(x):
        pass

    @Func
    def bar(x):
        return foo2(x)

    @Foreign
    def cow(x):
        pass

    @Foreign
    def duck(x):
        pass

    @Func
    def start_fn(x):
        a = foo(x)
        b = bar(a)
        return If(b, cow(x), duck(x))

    generate_dotviz(start_fn)
