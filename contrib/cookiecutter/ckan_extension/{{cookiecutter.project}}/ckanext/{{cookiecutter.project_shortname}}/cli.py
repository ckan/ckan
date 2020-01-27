import click

__all__ = ['{{cookiecutter.project_shortname}}']


@click.group()
def {{cookiecutter.project_shortname}}():
    """{{cookiecutter.project_shortname}} CLI.
    """
    pass

@{{cookiecutter.project_shortname}}.command()
def command():
    """Docs.
    """
    click.echo('Hello, {{cookiecutter.project_shortname}}!')


def get_commands():
    return [{{cookiecutter.project_shortname}}]
