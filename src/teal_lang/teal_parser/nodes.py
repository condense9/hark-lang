"""Nodes used to create the Teal AST"""

from typing import Any
from dataclasses import dataclass


@dataclass
class N_Definition:
    name: str
    paramlist: list
    body: list


@dataclass
class N_Lambda:
    paramlist: list
    body: list


@dataclass
class N_Import:
    name: str
    mod: str


@dataclass
class N_Call:
    fn: Any
    args: list


@dataclass
class N_Async:
    expr: str


@dataclass
class N_Await:
    expr: list


@dataclass
class N_Binop:
    lhs: Any
    op: str
    rhs: Any


@dataclass
class N_If:
    cond: Any
    then: list
    els: list


@dataclass
class N_Progn:
    exprs: list


@dataclass
class N_Id:
    name: str


@dataclass
class N_Symbol:
    name: str


@dataclass
class N_Argument:
    symbol: str
    value: Any


@dataclass
class N_Literal:
    value: Any
