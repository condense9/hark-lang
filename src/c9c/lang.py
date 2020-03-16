"""Really we're building an AST

Reimplementing a lisp-like structure.

"""
import inspect
import itertools
from dataclasses import dataclass
from collections import deque
from functools import singledispatch, wraps
from typing import List


class CompileError(Exception):
    pass


class Node:
    """An AST is built from nodes and edges

    Nodes are expressions to be evaluated. Edges are "sub-expressions" that must
    be evaluated first. Sub-expressions may be shared.

    There are a few primitives (values that evaluate to themselves, and are not
    parameterised): Symbols, Numbers, Strings, TODO...

    All leaf nodes are primitives (no parameters/children).

    """

    _count = 0

    def __init__(self, *operands):
        Node._count += 1
        self._name = f"N{Node._count}"
        self.operands = [Quote(o) if not isinstance(o, Node) else o for o in operands]

    @property
    def name(self):
        return self._name

    @property
    def descendents(self) -> list:
        """Get all descendent nodes"""
        operand_descendents = [[n] + n.descendents for n in self.operands]
        return list(itertools.chain.from_iterable(operand_descendents))

    def __repr__(self):
        kind = type(self).__name__
        return f"<{kind} {self.name}>"

    def __eq__(self, other):
        return type(self) == type(other) and all(
            a == b for a, b in zip(self.operands, other.operands)
        )


class Symbol(Node):
    """A symbolic value"""

    def __init__(self, name):
        super().__init__(name)
        self.symbol_name = name

    @property
    def descendents(self):
        return []


@singledispatch
def quote_value(value):
    return value


class VList(list):
    pass


@quote_value.register
def _(value: list):
    return VList(value)


class Quote(Node):
    """This is a bit more like a Quote... represent a real/primitive value"""

    def __init__(self, value):
        super().__init__()
        # Set operands manually - don't pass in to super().__init__ because it
        # will try to create a Quote, which will try to... etc
        self.value = value
        # TODO check allowed operand types?? Or anything goes...

    def unquote(self):
        return quote_value(self.value)

    @property
    def descendents(self):
        return []

    def __eq__(self, other):
        return isinstance(other, Quote) and self.unquote() == other.unquote()


class If(Node):
    """Branching!"""

    def __init__(self, cond, then, els):
        super().__init__([cond, then, els])
        self.cond = cond
        self.then = then
        self.els = els

    def __repr__(self):
        return f"<If {self.cond} ? {self.then} : {self.els}>"


class Funcall(Node):
    """Call a function with some arguments"""

    def __init__(self, function, *args, run_async=True):
        if not isinstance(function, (Func, Symbol)):
            raise ValueError(f"{function} is not a Func/Symbol (it's {type(function)})")
        super().__init__(function, *args)
        self.run_async = run_async


class Asm(Node):
    """Literal assembly instructions to execute"""

    def __init__(self, captures: list, instructions: list):
        """Run some raw assembly.

        CAPTURES specifies the objects that the assembly will operate on

        This is similar to how inline asm works in GCC - InputOperands are
        specified, and the compiler ensures they are in the right registers.

        """
        # We only init with captures so that operands (and hence descendents)
        # are only the objects that this node operates on
        super().__init__(*captures)
        self.instructions = instructions

    # TODO define __eq__, since instructions are not in operands


# Call a foreign function
class FCall(Node):
    def __init__(self, *operands):
        super().__init__(*operands)
        self.function = operands[0]
        self.args = operands[1:]


class Func(Quote):
    def __init__(self, fn):
        self.label = "F_" + fn.__name__
        sig = inspect.signature(fn)
        self.num_args = len(sig.parameters)
        self._fn = fn

    def __call__(self, *args):
        args = [Quote(o) if not isinstance(o, Node) else o for o in args]
        return Funcall(self, *args)

    def unquote(self):
        return self.label

    def b_reduce(self, values):
        """Evaluate the function with arguments replaced with values"""
        return self._fn(*values)

    def __repr__(self):
        return f"<Func {self.label}>"


# builtin just needs to transform from an AST into a sequence
class Builtin(Node):
    def __repr__(self):
        return "$" + type(self).__name__.upper()


# These are not "instructions" strictly, they are some kind of built-in
# The __init__ forms are declared just for arity-checking.


class Eq(Builtin):
    """Check whether the top two items on the stack are equal"""

    def __init__(self, a, b):
        super().__init__(a, b)


class Atomp(Builtin):
    """Check whether something is an atom"""

    def __init__(self, a):
        super().__init__(a)


class Cons(Builtin):
    """Cons two elements together"""

    def __init__(self, a, b):
        super().__init__(a, b)


class Car(Builtin):
    """CAR (first element) of a list"""

    def __init__(self, a):
        super().__init__(a)


class Cdr(Builtin):
    """CDR (all elements after first) of a list"""

    def __init__(self, a):
        super().__init__(a)


class Nullp(Builtin):
    """Check whether the top item on the stack is NIL"""

    def __init__(self, a):
        super().__init__(a)


################################################################################


# Func could be made variadic by assigning self.num_args during __call__ and
# wrapping self._fn with a new function that takes a specific number of values.


# A "Type" is a function. So a string name (address) and a body. Some Types are
# builtin, which means their implementations are defined in machine.py, and they
# are skipped during the compile phase (no def/body generated for them).
#
# The compiler needs to know which machine it is targetting, so that it can skip
# generating definitions. 03/12/20


# How about... when a Node is called, it returns other Nodes. Then we'd get easy
# composition. Quote just returns itself. There are some primitive nodes, which
# return themselves, but others could return more nodes?! So in compiling, every
# non-primitive node calls itself and compiles the results.
#
# No. That's reimplementing what already exists - abstraction through defun.
# Cond can easily be defun'd, using the If primitive.


################################################################################
## Higher order.


@Func
def Map(function, lst):
    # function is a symbol referring to a function, so must Apply it
    return If(
        Nullp(lst),
        Quote([]),
        Cons(Funcall(function, Car(lst)), Map(function, Cdr(lst))),
    )


################################################################################
## Helpers


def traverse(fn) -> List[Node]:
    """List all nodes starting from root"""
    # This *requires* evaluation, and hence isn't possible (non-determinism).
    # Original, misguided attempt left below for posterity.
    raise Exception("Nope")
    children = [c for c in root.operands if isinstance(c, Node)]
    print("t ", root, children)
    if not children:
        return root
    else:
        return [root] + [traverse(c) for c in children]


def get_symbol_ops(fn):
    """List symbolic names of the parameters"""
    return [str(p) for p in signature(fn).parameters.keys()]


def visit(root, do):
    """Visit all nodes in a graph, in order of evaluation"""

    def _doit(node, visited):
        do(node)

        for child in node.operands:
            if child in visited:
                continue
            # XXX: not tested:
            if callable(child):
                visited += _doit(child.fn(*get_symbol_ops(child.fn)), visited + [child])
            else:
                visited += _doit(child, visited + [child])

        return visited

    do(root)
    _doit(root.fn(*get_symbol_ops(root.fn)), [])


def visit_collect(root):
    nodes = []
    visit(root, lambda x: nodes.append(x))
    return nodes


def eval_with(root, eval_fn, *, maxdepth=1):
    """postorder traversal of a node and its children"""

    def _doit(node, depth):
        for child in node.operands:
            # XXX: not tested:
            if callable(child) and depth < maxdepth:
                _doit(child.fn(*get_symbol_ops(child)), depth + 1)
            else:
                _doit(child, depth + 1)

        eval_fn(node)

    # eval_fn(root)
    _doit(root.fn(*get_symbol_ops(root.fn)), 1)


def childrennnn(root):
    children = []
    check = deque(root.operands)
    while check:
        this_node = check.popleft()
        children.append(this_node)
        # FIXME ugly - define which nodes do or don't have operands
        if hasattr(this_node, "operands"):
            check.extend(this_node.operands)
    return children


def eval_collect(root, *, maxdepth=1):
    nodes = []
    eval_with(root, lambda x: nodes.append(x), maxdepth=maxdepth)
    return nodes


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
