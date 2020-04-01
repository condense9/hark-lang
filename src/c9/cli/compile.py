"""The CLI"""

import click

from .. import c9exe

# from .service import Service


@click.command()
@click.argument("file")
@click.argument("output")
@click.option("-i", "--include", multiple=True)
def compile(file, output, include):
    """Compile file into a C9 executable"""
    c9exe.dump(file, output, include)


if __name__ == "__main__":
    compile()
