from collections.abc import Iterable
from functools import singledispatchmethod
import hashlib

import pydot

from .nodes import *


class NodeStyles:
    conditional = {"shape": "diamond", "fillcolor": "yellow"}
    default = {}


class ASTGenerator:

    _PRINTABLE_TYPES = (str, int, float, bool, bytes, )

    def __init__(self, node_list, graph_name=None):
        self.graph = pydot.Dot(graph_type="graph", graph_name=graph_name)
        self.node_type_counts = {}
        self.graph_nodes = {}
        for n in node_list:
            self.recurse_tree(n)

    def connect_nodes(self, node_a, node_b, label=None):
        self.graph.add_edge(pydot.Edge(node_a, node_b, label=label))

    @classmethod
    def _class_name(self, teal_node):
        return teal_node.__class__.__name__

    @classmethod
    def node_hash(cls, teal_node):
        data = [getattr(teal_node, k) for k in ["source_filename", "source_lineno", "source_line",
                                                "source_column"]]
        return hashlib.sha224("{}:{}".format(cls._class_name(teal_node), str(data))).hexdigest()

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
        return "{}:{}".format(self._class_name(teal_node), teal_node.expr)

    @_teal_node_label.register
    def _(self, teal_node: N_Import):
        return "{}:{}:{}".format(self._class_name(teal_node), teal_node.name, teal_node.mod)

    @_teal_node_label.register
    def _(self, teal_node: N_Call):
        return self._attempt_label_from(teal_node, "fn")

    @_teal_node_label.register
    def _(self, teal_node: N_Argument):
        label = "{}:{}".format(self._class_name(teal_node), teal_node.symbol)
        if isinstance(teal_node.value, self._PRINTABLE_TYPES):
            label += ":{}".format(teal_node.value)
        return label

    @_teal_node_label.register
    def _(self, teal_node: N_Literal):
        return self._attempt_label_from(teal_node, "value")

    def node(self, teal_node):
        node_hash = self.node_hash(teal_node)
        if node_hash in self.graph_nodes:
            return self.graph_nodes[node_hash]

        kwargs = {"label": self._teal_node_label(teal_node)}
        kwargs.update(self._teal_node_style(teal_node))

        return pydot.Node(node_hash, **kwargs)

    def _recurse_type_any(self, teal_node, attribute_name):
        attr = getattr(teal_node, attribute_name)
        root_graph_node = self.node(teal_node)
        if isinstance(attr, Iterable):
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
        for n in teal_node.body:
            self.connect_nodes(root_graph_node, self.recurse_tree(n))
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Lambda):
        root_graph_node = self.node(teal_node)
        for i, n in enumerate(teal_node.paramlist):
            self.connect_nodes(root_graph_node, self.recurse_tree(n), label="param_{}".format(i))
        for i, n in enumerate(teal_node.body):
            self.connect_nodes(root_graph_node, self.recurse_tree(n), label="body_{}".format(i))
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Call):
        root_graph_node = self.node(teal_node)
        for i, n in enumerate(teal_node.args):
            self.connect_nodes(root_graph_node, self.recurse_tree(n), label="arg_{}".format(i))
        self._recurse_type_any(teal_node, "fn")
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Await):
        root_graph_node = self.node(teal_node)
        for n in teal_node.expr:
            self.connect_nodes(root_graph_node, self.recurse_tree(n))
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
        for i, n in enumerate(teal_node.then):
            self.connect_nodes(root_graph_node, self.recurse_tree(n), label="then_{}".format(i))
        for i, n in enumerate(teal_node.els):
            self.connect_nodes(root_graph_node, self.recurse_tree(n), label="els_{}".format(i))
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_Progn):
        root_graph_node = self.node(teal_node)
        for n in teal_node.exprs:
            self.connect_nodes(root_graph_node, self.recurse_tree(n))
        return root_graph_node

    @recurse_tree.register
    def _(self, teal_node: N_MultipleValues):
        root_graph_node = self.node(teal_node)
        for n in teal_node.exprs:
            self.connect_nodes(root_graph_node, self.recurse_tree(n))
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

    def write(self, path):
        self.graph.write(path)
