# -*- coding: utf-8 -*-
from __future__ import annotations

import click

import ckan.plugins.toolkit as tk


@click.command(u"example-iclick-hello")
def hello_cmd():
    """Example of single command.
    """
    click.secho(u"Hello, World!", fg=u"green")


@click.group(u"example-iclick-bye")
def bye_cmd():
    """Example of group of commands.
    """
    pass


@bye_cmd.command()
@click.argument(u"name", required=False)
def bye(name: str):
    """Command with optional argument.
    """
    if not name:
        tk.error_shout(u"I do not know your name.")
    else:
        click.secho(u"Bye, {}".format(name))


def get_commands() -> list[click.Command]:
    return [hello_cmd, bye_cmd]
