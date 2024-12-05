import click


@click.group(short_help="statistical_org CLI.")
def statistical_org():
    """statistical_org CLI.
    """
    pass


@statistical_org.command()
@click.argument("name", default="statistical_org")
def command(name):
    """Docs.
    """
    click.echo("Hello, {name}!".format(name=name))


def get_commands():
    return [statistical_org]
