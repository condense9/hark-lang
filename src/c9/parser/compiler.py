"""Compile a file into a set of definitions and code"""

import c9.machine.instructionset as mi
from lark import Token

from .load import file_parser
from c9.parser.read import read
from .evaluate import evaluate
