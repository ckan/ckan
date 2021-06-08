import click


@click.group(short_help="{{cookiecutter.project_shortname}} CLI.")
def {{cookiecutter.project_shortname}}():
    """{{cookiecutter.project_shortname}} CLI.
    """
    pass


@{{cookiecutter.project_shortname}}.command()
@click.argument("name", default="{{cookiecutter.project_shortname}}")
def command(name):
    """Docs.
    """
    click.echo("Hello, {name}!".format(name=name))


def get_commands():
    return [{{cookiecutter.project_shortname}}]
