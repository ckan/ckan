# -*- coding: utf-8 -*-

import click
import ckan.plugins.toolkit as tk


@click.command("example-iclick-hello")
def hello_cmd():
    """Example of single command.
    """
    click.secho("Hello, World!", fg="green")


@click.group("example-iclick-bye")
def bye_cmd():
    """Example of group of commands.
    """
    pass


@bye_cmd.command()
@click.argument("name", required=False)
def bye(name):
    """Command with optional argument.
    """
    if not name:
        tk.error_shout("I do not know your name.")
    else:
        click.secho("Bye, {}".format(name))


def get_commands():
    return [hello_cmd, bye_cmd]
