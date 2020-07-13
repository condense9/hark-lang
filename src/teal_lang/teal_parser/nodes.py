"""Nodes used to create the Teal AST"""

from typing import Any, Union
from dataclasses import dataclass


@dataclass
class Node:
    source_filename: str
    source_lineno: str
    source_line: str
    source_column: int

    @classmethod
    def from_node(cls, other, *args, **kwargs):
        """Make a new Node that inherits source information from another node"""
        return cls(
            other.source_filename,
            other.source_lineno,
            other.source_line,
            other.source_column,
            *args,
            **kwargs
        )


@dataclass
class N_Definition(Node):
    name: str
    paramlist: list
    body: list
    attribute: Union[str, None] = None


@dataclass
class N_Lambda(Node):
    paramlist: list
    body: list


@dataclass
class N_Import(Node):
    name: str
    mod: str


@dataclass
class N_Call(Node):
    fn: Any
    args: list


@dataclass
class N_Async(Node):
    expr: str


@dataclass
class N_Await(Node):
    expr: list


@dataclass
class N_Binop(Node):
    lhs: Any
    op: str
    rhs: Any


@dataclass
class N_If(Node):
    cond: Any
    then: list
    els: list


@dataclass
class N_Progn(Node):
    """List of expressions, but only the last evaluation result is kept"""

    exprs: list


@dataclass
class N_MultipleValues(Node):
    """Like progn, but all results are kept"""

    exprs: list


@dataclass
class N_Id(Node):
    name: str


@dataclass
class N_Symbol(Node):
    name: str


@dataclass
class N_Argument(Node):
    symbol: str
    value: Any


@dataclass
class N_Literal(Node):
    value: Any


@dataclass
class N_Label(Node):
    name: str


@dataclass
class N_Goto(Node):
    name: str
