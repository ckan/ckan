import click


@click.group(short_help="logs CLI.")
def logs():
    """logs CLI.
    """
    pass


@logs.command()
@click.argument("name", default="logs")
def command(name):
    """Docs.
    """
    click.echo("Hello, {name}!".format(name=name))


def get_commands():
    return [logs]
