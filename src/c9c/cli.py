"""The CLI"""

import click

from . import synthesiser
from .service import Service


@click.group()
@click.pass_obj
def cli(obj, region, provider):
    assert isinstance(obj, Service)
    pass


@cli.command()
@click.option("-o", "--output", "output_dir", default="build")
@click.option("-p", "--provider", "provider", default="aws")
@click.option("-r", "--region", default="eu-west-1")
@click.pass_obj
def generate(ctx, output_dir, provider, region):
    synthesiser.generate(ctx.obj, output_dir)
