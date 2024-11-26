import click


@click.group(short_help="tracking_datatypes CLI.")
def tracking_datatypes():
    """tracking_datatypes CLI.
    """
    pass


@tracking_datatypes.command()
@click.argument("name", default="tracking_datatypes")
def command(name):
    """Docs.
    """
    click.echo("Hello, {name}!".format(name=name))


def get_commands():
    return [tracking_datatypes]
