from uuid import uuid4
import pytest

from hark_lang.hark_parser.nodes import Node, N_Label
from hark_lang.hark_parser.ast_tree import ASTGenerator


def string_attributes(Node, ignore_attrs=None):
    """
    Return tuple of (list of string attributes, list of non-string attributes)
    """
    if not ignore_attrs:
        ignore_attrs = ['source_filename', 'source_lineno', 'source_line', 'source_column',
                        'attribute']
    attrs = [k for k in Node.__dataclass_fields__.keys() if k not in ignore_attrs]
    str_attrs = [a for a in attrs if Node.__dataclass_fields__[a].type == str]
    return str_attrs, [a for a in attrs if a not in str_attrs]


NODES = Node.__subclasses__()
LEAF_NODES = [n for n in NODES if not string_attributes(n)[1]]
NULL_ARGS = [None] * 4


def list_generator(length=2):
    ustr = str(uuid4())
    return [N_Label(*NULL_ARGS, name="label_{}_{}".format(ustr, i)) for i in range(length)]


def node_generator():
    ustr = str(uuid4())
    return N_Label(*NULL_ARGS, name="label_{}".format(ustr))


def node_equality(graph_node_a, graph_node_b):
    return graph_node_a.get_name() == graph_node_b.get_name() and \
           graph_node_a.get_label() == graph_node_b.get_label()


def check_edges(ast_enerator, graph_nodes, graph_edges, sub_n, gn, attr_name, attr_i=None):
    node_matches = [sub_gn for sub_gn in graph_nodes if node_equality(ast_enerator.node(sub_n),
                                                                      sub_gn)]
    assert len(node_matches) == 1
    sub_gn = node_matches[0]
    edge_matches = [e for e in graph_edges if e.get_source() == gn.get_name()
                    and e.get_destination() == sub_gn.get_name()]
    assert len(edge_matches) == 1
    edge = edge_matches[0]
    if attr_i is None:
        assert edge.obj_dict['attributes']['label'] == attr_name
    else:
        assert edge.obj_dict['attributes']['label'] == "{}_{}".format(attr_name, attr_i)
    return edge


@pytest.mark.parametrize("RootNode", NODES)
@pytest.mark.parametrize("leaf_generator", [list_generator, node_generator])
def test_recursion(RootNode, leaf_generator):
    """
    Testing whether all the edges are created according to the Node attributes. Naming of edges
    is checked, but not naming of graph nodes
    """
    str_attrs, non_str_attrs = string_attributes(RootNode)
    kwargs = {a: "str_{}".format(i) for i, a in enumerate(str_attrs)}
    kwargs.update({a: leaf_generator() for i, a in enumerate(non_str_attrs)})

    n = RootNode(*NULL_ARGS, **kwargs)

    ag = ASTGenerator([n])

    graph = ag.graph

    graph_edges = graph.get_edges()
    graph_nodes = graph.get_nodes()

    assert node_equality(ag.node(n), graph_nodes[0])
    gn = graph_nodes[0]

    seen_edges = []

    for k, v in kwargs.items():
        if isinstance(v, list):
            for i, sub_n in enumerate(v):
                seen_edges.append(check_edges(ag, graph_nodes, graph_edges, sub_n, gn, k, i))

        elif isinstance(v, Node):
            seen_edges.append(check_edges(ag, graph_nodes, graph_edges, v, gn, k))

    assert len(seen_edges) == len(graph_edges)
    assert set(seen_edges) == set(graph_edges)
