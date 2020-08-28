from functools import singledispatchmethod
import hashlib
from pathlib import Path
import os
from uuid import uuid4

import pydot

from .nodes import *
from .parser import tl_parse


class NodeStyles:
    conditional = {"shape": "diamond", "fillcolor": "yellow"}
    default = {}


class ASTGenerator:

    _PRINTABLE_TYPES = (str, int, float, bool, bytes, )

    def __init__(self, node_list, graph_name=None):
        self.graph = pydot.Dot(graph_type="graph", graph_name=graph_name)
        self.node_type_counts = {}
        self._teal_nodes = []
        self._graph_nodes = []
        for n in node_list:
            self.recurse_tree(n)

    def connect_nodes(self, node_a, node_b, label=None):
        if label is None:
            # pydot doesn't handle None values correctly
            self.graph.add_edge(pydot.Edge(node_a, node_b))
        else:
            self.graph.add_edge(pydot.Edge(node_a, node_b, label=label))

    @classmethod
    def _class_name(self, teal_node):
        return teal_node.__class__.__name__

    @classmethod
    def node_hash(cls, teal_node):
        data = [getattr(teal_node, k) for k in ["source_filename", "source_lineno", "source_line",
                                                "source_column"]]
        return hashlib.sha224("{}:{}".format(cls._class_name(teal_node), str(data)).encode()).hexdigest()

    @singledispatchmethod
    def _teal_node_style(self, teal_node: Node):
        return NodeStyles.default

    @_teal_node_style.register
    def _(self, teal_node: N_If):
        return NodeStyles.conditional

    def _nameless_node_label(self, teal_node):
        class_name = self._class_name(teal_node)
        if class_name not in self.node_type_counts:
            self.node_type_counts[class_name] = 0

        label = "{}_{}".format(class_name, self.node_type_counts[class_name])
        self.node_type_counts[class_name] += 1
        return label

    def _attempt_label_from(self, teal_node, attribute):
        attr = getattr(teal_node, attribute)
        if isinstance(attr, self._PRINTABLE_TYPES):
            return "{}:{}".format(self._class_name(teal_node), attr)
        else:
            return self._nameless_node_label(teal_node)

    @singledispatchmethod
    def _teal_node_label(self, teal_node: Node):
        if hasattr(teal_node, "name"):
            return "{}:{}".format(self._class_name(teal_node), teal_node.name)
        else:
            return self._nameless_node_label(teal_node)

    @_teal_node_label.register
    def _(self, teal_node: N_Binop):
        return "{}:{}".format(self._class_name(teal_node), teal_node.op)

    @_teal_node_label.register
    def _(self, teal_node: N_Async):
        if isinstance(teal_node.expr, self._PRINTABLE_TYPES):
            return "{}:{}".format(self._class_name(teal_node), teal_node.expr)
        else:
            return "{}".format(self._class_name(teal_node))

    @_teal_node_label.register
    def _(self, teal_node: N_Import):
        return "{}:{}:{}".format(self._class_name(teal_node), teal_node.name, teal_node.mod)

    @_teal_node_label.register
    def _(self, teal_node: N_Call):
        return self._attempt_label_from(teal_node, "fn")

    @_teal_node_label.register
    def _(self, teal_node: N_Argument):
        label = self._class_name(teal_node)
        if isinstance(teal_node.symbol, self._PRINTABLE_TYPES):
            label += ":{}".format(teal_node.symbol)
        if isinstance(teal_node.value, self._PRINTABLE_TYPES):
            label += ":{}".format(teal_node.value)
        return label

    @_teal_node_label.register
    def _(self, teal_node: N_Literal):
        return self._attempt_label_from(teal_node, "value")

    def node(self, teal_node):
        if teal_node not in self._teal_nodes:
            # Need to put double-quote label since pydot doesn't do escaping or checks for that
            kwargs = {"label": '"{}"'.format(self._teal_node_label(teal_node))}
            kwargs.update(self._teal_node_style(teal_node))

            self._teal_nodes.append(teal_node)
            self._graph_nodes.append(pydot.Node(str(uuid4()), **kwargs))
            self.graph.add_node(self._graph_nodes[-1])
        return self._graph_nodes[self._teal_nodes.index(teal_node)]

    def _recurse_type_any(self, teal_node, attribute_name):
        attr = getattr(teal_node, attribute_name)
        root_graph_node = self.node(teal_node)
        if isinstance(attr, list):
            for i, n in enumerate(attr):
                self.connect_nodes(root_graph_node, self.recurse_tree(n), label="{}_{}".format(
                    attribute_name, i))
        elif isinstance(attr, Node):
            self.connect_nodes(root_graph_node, self.recurse_tree(attr), label=attribute_name)

    @singledispatchmethod
    def recurse_tree(self, teal_node: Node):
        return self.node(teal_node)

    @recurse_tree.register
    def _(self, teal_node: N_Definition):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "body")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Lambda):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "paramlist")
        self._recurse_type_any(teal_node, "body")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Call):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "args")
        self._recurse_type_any(teal_node, "fn")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Await):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "expr")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Binop):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "lhs")
        self._recurse_type_any(teal_node, "rhs")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_If):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "cond")
        self._recurse_type_any(teal_node, "then")
        self._recurse_type_any(teal_node, "els")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Progn):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "exprs")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_MultipleValues):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "exprs")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Argument):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "value")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Literal):
        root_graph_node = self.node(teal_node)
        self._recurse_type_any(teal_node, "value")
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