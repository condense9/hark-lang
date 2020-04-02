"""Languge Node -> Machine Instruction

| Node                             | Evaluates to (pushed on stack)
|----------------------------------|---------------------------------------
| Funcall Function(f) [Node](args) | f(args)
| If Node(c) Node(a) Node(b)       | if c == True then a else b
| Value x                          | Value(x) (constructor)
| Do [Node]                        | result of evaluating last node (progn)

We could do with some kind of loop (compile-time function-local label/goto would
be fairly trivial to implement).

"""

from dataclasses import dataclass
from functools import singledispatch
from typing import List, Tuple, Dict

from .. import lang as l
from .. import machine as m
from .compiler_utils import traverse_dag, flatten, pairwise


class CompileError(Exception):
    pass


@dataclass
class CodeObject:
    """Manage a chunk of code to be passed around in the compiler"""

    code: list  # List[Instruction]

    def __init__(self, code):
        self.code = code
        for i in code:
            if isinstance(i, CodeObject):
                raise Exception("Got CodeObject - did you forget `.code`?")
            if not isinstance(i, m.Instruction):
                raise Exception(f"Bad code {i} ({type(i)})")
            for o in i.operands:
                if not isinstance(o, (str, int, list)) and not callable(o):
                    raise Exception(f"Bad operand {o} ({type(o)})")


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
def _(node: l.Funcall) -> CodeObject:
    """Call a C9 Function"""
    arg_code = flatten(compile_node(arg).code for arg in reversed(node.operands))
    if not isinstance(node.blocking, bool):
        raise CompileError(f"{node} blocking isn't known at compile-time")
    call_cls = m.Call if node.blocking else m.ACall
    # TODO auto-detect oportunities for ACall??
    return CodeObject([*arg_code, call_cls(len(node.operands) - 1)])


@compile_node.register
def _(node: l.ForeignCall) -> CodeObject:
    """Call a native Python function"""
    arg_code = flatten(compile_node(arg).code for arg in node.args)
    num_args = len(node.args)
    waits = [m.Wait(i) for i in range(num_args)]
    return CodeObject(
        [
            # --
            *arg_code,
            *waits,  # All arguments must be resolved first!
            m.MFCall(node.function, num_args,)
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


def compile_all(fn: l.Func) -> Dict[str, List[m.Instruction]]:
    """Compile FN and all functions called by FN"""
    return {
        n.label: compile_function(n) for n in traverse_dag(fn) if isinstance(n, l.Func)
    }


def compile_function(fn: l.Func) -> List[m.Instruction]:
    """Compile function into machine instructions"""
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

    return body
