"""

Node -> Instruction

NOTE: no variables

| Node                             | Evaluates to (pushed on stack)
|----------------------------------|---------------------------------------
| Funcall Function(f) [Node](args) | f(args)
| If Node(c) Node(a) Node(b)       | if c == True then a else b
| Value x                          | Value(x) (constructor)
| Do [Node]                        | result of evaluating last node (progn)

"""

from dataclasses import dataclass
from functools import singledispatch
from typing import List, Tuple

import lang as l
import machine as m
from compiler_utils import map_funcs, flatten


@dataclass
class CodeObject:
    code: list  # List[Instruction]

    def __init__(self, code):
        self.code = code
        for i in code:
            if isinstance(i, CodeObject):
                raise Exception("Got CodeObject - did you forget `.code`?")
            if not isinstance(i, (m.Instruction, l.Builtin)):
                raise Exception(f"Bad code {i} ({type(i)})")


@singledispatch
def compile_node(node: l.Node) -> CodeObject:
    """Take an AST node and (recursively) compile it into machine code"""
    raise NotImplementedError(node, type(node))


@compile_node.register
def _(node: l.Quote) -> CodeObject:
    """Quote: just unquote it and push the value"""
    return CodeObject([m.PushV(node.unquote())])


@compile_node.register
def _(node: l.Symbol) -> CodeObject:
    """Symbol: create a binding and push that"""
    # NOTE - it's not quite the same as Quote, because of the PushB
    return CodeObject([m.PushB(node.symbol_name)])


@compile_node.register
def _(node: l.Asm) -> CodeObject:
    """Raw machine instructions"""
    arg_code = flatten(compile_node(arg).code for arg in node.operands)
    return CodeObject(arg_code + node.instructions)


@compile_node.register
def _(node: l.Builtin) -> CodeObject:
    """Builtin: call a machine instruction of the same name"""
    arg_code = flatten(compile_node(arg).code for arg in node.operands)
    return CodeObject(
        [
            # --
            *arg_code,
            node,  # This node is "primitive"! The machine must implement it
            # --
        ]
    )


@compile_node.register
def _(node: l.Funcall) -> CodeObject:
    """Call a C9 Function"""
    arg_code = flatten(compile_node(arg).code for arg in reversed(node.operands))
    wait = [] if node.run_async else [m.Wait()]
    return CodeObject([*arg_code, m.Call()] + wait)


@compile_node.register
def _(node: l.ForeignCall) -> CodeObject:
    """Call a native Python function"""
    arg_code = flatten(compile_node(arg).code for arg in node.args)
    num_args = len(node.args)
    waits = [m.Wait() for _ in range(num_args)]
    return CodeObject(
        [
            # --
            *arg_code,
            *waits,  # All arguments must be resolved first!
            m.MFCall(node.function, num_args)
            # --
        ]
    )


@compile_node.register
def _(node: l.If) -> CodeObject:
    """Branching"""
    cond = compile_node(node.cond)
    branch_true = compile_node(node.then)
    branch_false = compile_node(node.els)
    return CodeObject(
        [
            # --
            *cond.code,
            m.PushV(True),  # or something like VTrue :: Bool
            m.JumpIE(len(branch_false.code) + 1),  # to branch_true
            *branch_false.code,
            m.Jump(len(branch_true.code)),  # to Return
            *branch_true.code,
            # --
        ],
    )


@compile_node.register
def _(node: l.Do) -> CodeObject:
    """Evaluate all arguments"""
    arg_code = flatten(compile_node(arg).code for arg in node.operands)
    return CodeObject(arg_code)


################################################################################
## Node spec done - now compile them.


def compile_all(fn: l.Func, target_machine=None) -> dict:
    return map_funcs(fn, compile_function)


def compile_function(fn: l.Func) -> Tuple[List[m.Instruction], List[l.Func]]:
    """Compile function and list other functions it calls"""
    # Bind the arguments so they can be used later
    bindings, placeholders = list(
        zip(*[(m.Bind(i), l.Symbol(i)) for i in range(fn.num_args)])
    )
    node = fn.b_reduce(placeholders)
    fn_compiled = compile_node(node)
    body = [
        # --
        *bindings,
        *fn_compiled.code,
        m.Return(),
        # --
    ]

    calls = []
    new_nodes = node.descendents
    for n in new_nodes:
        if isinstance(n, l.Func) and n not in calls:
            calls.append(n)

    return body, calls
