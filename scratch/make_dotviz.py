"""In development - create dotviz from DAG"""


def fn_dot(root_node) -> list:
    """Return the lines of the graph body"""
    nodes = []
    edges = []

    if not isinstance(root_node, Node):
        root_node = root_node(*get_symbol_ops(root_node))

    for node in eval_collect(root_node):
        # XXX: not tested:
        shape = "box" if callable(node) else "oval"
        nodes.append(f'{node.name} [label="{node}" shape={shape}];')

        for c in node.operands:
            edges.append(f"{node.name} -> {c.name};")

    return nodes + edges


def to_dot(root_node) -> str:
    if not isinstance(root_node, Node):
        root_node = root_node(*get_symbol_ops(root_node))

    # root_body = fn_dot(root_node)

    subs = []
    for node in [root_node] + eval_collect(root_node):
        if isinstance(node, Func):
            styles = [f'label = "{node.name}";', "color=lightgrey"]
            lines = fn_dot(node) + styles
            body = "\n    ".join(lines)
            subs.append(body)

    # https://graphviz.gitlab.io/_pages/Gallery/directed/cluster.html
    # body = "\n  ".join(root_body) + "\n\n  " + "\n\n  ".join(subs)
    body = "\n\n  ".join(
        f"subgraph cluster_{i} {{\n{body}}}" for i, body in enumerate(subs)
    )
    return f"digraph {root_node.name} {{\n  {body}\n}}"
