"""Attributes handling"""

# Inspiration: https://doc.rust-lang.org/reference/attributes.html

# https://github.com/condense9/teal-lang/blob/parsers/parser_experiments/parsec.py

# https://parsy.readthedocs.io/en/latest/
import parsy

# TODO


def parse_attribute(attr: str) -> dict:
    """Parse an attribute string into a dictionary"""
