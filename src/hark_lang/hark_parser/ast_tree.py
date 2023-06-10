from functools import singledispatchmethod
from pathlib import Path
import os
from uuid import uuid4

import pydot

from ..hark_parser import nodes
from .parser import tl_parse


class NodeStyles:
    conditional = {"shape": "diamond", "fillcolor": "yellow"}
    default = {}


class ASTGenerator:

    _PRINTABLE_TYPES = (str, int, float, bool, bytes, )

    def __init__(self, node_list, graph_name=None):
        self.graph = pydot.Dot(graph_type="graph", graph_name=graph_name)
        self.node_type_counts = {}
        self._hark_nodes = []
        self._graph_nodes = []
        for n in node_list:
            self.recurse_tree(n)

    def connect_nodes(self, src_node, dest_node, label=None):
        if label is None:
            # pydot doesn't handle None values correctly
            self.graph.add_edge(pydot.Edge(src_node, dest_node))
        else:
            self.graph.add_edge(pydot.Edge(src_node, dest_node, label=label))

    @classmethod
    def _class_name(self, hark_node):
        return hark_node.__class__.__name__

    @singledispatchmethod
    def _hark_node_style(self, hark_node: nodes.Node):
        return NodeStyles.default

    @_hark_node_style.register
    def _(self, hark_node: nodes.N_If):
        return NodeStyles.conditional

    def _nameless_node_label(self, hark_node):
        class_name = self._class_name(hark_node)
        if class_name not in self.node_type_counts:
            self.node_type_counts[class_name] = 0

        label = "{}_{}".format(class_name, self.node_type_counts[class_name])
        self.node_type_counts[class_name] += 1
        return label

    def _attempt_label_from(self, hark_node, attribute):
        attr = getattr(hark_node, attribute)
        if isinstance(attr, self._PRINTABLE_TYPES):
            return "{}:{}".format(self._class_name(hark_node), attr)
        else:
            return self._nameless_node_label(hark_node)

    @singledispatchmethod
    def _hark_node_label(self, hark_node: nodes.Node):
        if hasattr(hark_node, "name"):
            return "{}:{}".format(self._class_name(hark_node), hark_node.name)
        else:
            return self._nameless_node_label(hark_node)

    @_hark_node_label.register
    def _(self, hark_node: nodes.N_Binop):
        return "{}:{}".format(self._class_name(hark_node), hark_node.op)

    @_hark_node_label.register
    def _(self, hark_node: nodes.N_Async):
        if isinstance(hark_node.expr, self._PRINTABLE_TYPES):
            return "{}:{}".format(self._class_name(hark_node), hark_node.expr)
        else:
            return "{}".format(self._class_name(hark_node))

    @_hark_node_label.register
    def _(self, hark_node: nodes.N_Import):
        return "{}:{}:{}".format(self._class_name(hark_node), hark_node.name, hark_node.mod)

    @_hark_node_label.register
    def _(self, hark_node: nodes.N_Call):
        return self._attempt_label_from(hark_node, "fn")

    @_hark_node_label.register
    def _(self, hark_node: nodes.N_Argument):
        label = self._class_name(hark_node)
        if isinstance(hark_node.symbol, self._PRINTABLE_TYPES):
            label += ":{}".format(hark_node.symbol)
        if isinstance(hark_node.value, self._PRINTABLE_TYPES):
            label += ":{}".format(hark_node.value)
        return label

    @_hark_node_label.register
    def _(self, hark_node: nodes.N_Literal):
        return self._attempt_label_from(hark_node, "value")

    def node(self, hark_node):
        if hark_node not in self._hark_nodes:
            # Need to put double-quote label since pydot doesn't do escaping or checks for that
            kwargs = {"label": '"{}"'.format(self._hark_node_label(hark_node))}
            kwargs.update(self._hark_node_style(hark_node))

            self._hark_nodes.append(hark_node)
            self._graph_nodes.append(pydot.Node(str(uuid4()), **kwargs))
            self.graph.add_node(self._graph_nodes[-1])
        return self._graph_nodes[self._hark_nodes.index(hark_node)]

    def _recurse_type_any(self, hark_node, attribute_name):
        attr = getattr(hark_node, attribute_name)
        root_graph_node = self.node(hark_node)
        if isinstance(attr, list):
            for i, n in enumerate(attr):
                self.connect_nodes(root_graph_node, self.recurse_tree(n), label="{}_{}".format(
                    attribute_name, i))
        elif isinstance(attr, nodes.Node):
            self.connect_nodes(root_graph_node, self.recurse_tree(attr), label=attribute_name)

    @singledispatchmethod
    def recurse_tree(self, hark_node: nodes.Node):
        return self.node(hark_node)

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Definition):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "paramlist")
        self._recurse_type_any(hark_node, "body")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Lambda):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "paramlist")
        self._recurse_type_any(hark_node, "body")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Call):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "args")
        self._recurse_type_any(hark_node, "fn")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Await):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "expr")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Binop):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "lhs")
        self._recurse_type_any(hark_node, "rhs")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_If):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "cond")
        self._recurse_type_any(hark_node, "then")
        self._recurse_type_any(hark_node, "els")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Progn):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "exprs")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_MultipleValues):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "exprs")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Argument):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "value")
        return root_graph_node

    @recurse_tree.register
    def _(self, hark_node: nodes.N_Literal):
        root_graph_node = self.node(hark_node)
        self._recurse_type_any(hark_node, "value")
        return root_graph_node

    def write_png(self, path):
        self.graph.write(path, format="png")

    def write_raw(self, path):
        self.graph.write(path, format="raw")


def ast_tree(filename: Path) -> ASTGenerator:
    "Compile a Teal file, creating an Executable ready to be used"
    with open(filename, "r") as f:
        text = f.read()

    node_list = tl_parse(filename, text, debug_lex=os.getenv("DEBUG_LEX", False))
    return ASTGenerator(node_list)
