from lark import Tree, Transformer

# Node : Branch | Terminal
#
# Branch : Funcall Node*
#        | ForeignCall Node*
#        | If cond then else
#        | Do Node*
#        | Asm (?)
#
# Terminal: Literal | Symbol


# e.g.
#
# def foo: print "hi"
#
# -> {"foo": Funcall(Func("print"), "hi")}


class C9Transformer(Transformer):
    def expr(self, args):
        return eval(args[0])


class F(Visitor):


def get_functions(tree):
