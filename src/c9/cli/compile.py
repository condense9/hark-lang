"""The CLI"""

import click

from .. import py_to_c9e


@click.command()
@click.argument("file")
@click.argument("output")
@click.option("-i", "--include", multiple=True)
def compile(file, output, include):
    """Compile file into a C9 executable"""
    py_to_c9e.dump(file, output, include)


if __name__ == "__main__":
    compile()
