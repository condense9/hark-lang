"""Load the Teal parser"""
import os.path

import lark

GRAMMAR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "grammar.lark")


def file_parser():
    return lark.Lark.open(GRAMMAR, parser="lalr", start="file")


def exp_parser():
    return lark.Lark.open(GRAMMAR, parser="lalr", start="sexp")
