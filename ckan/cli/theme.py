from __future__ import annotations

import logging

import click

from ckan.common import config
from ckan.lib import theme as lib_theme
from . import error_shout

log = logging.getLogger(__name__)


@click.group(name="theme", short_help="Theme related commands.")
def theme():
    pass


@theme.command("list")
def list_themes():
    """List available themes."""
    themes = lib_theme.collect_themes()
    for name, info in themes.items():
        click.echo(name)
        click.echo(f"\tPath: {info.path}")

        lineage = []
        parent = info.extends
        while parent:
            if parent_info := themes.get(parent):
                lineage.append(parent)
                parent = parent_info.extends
            else:
                lineage.append(click.style(parent, fg="red"))

        if lineage:
            click.secho(f"\tExtends: {' -> '.join(lineage)}")


@theme.command("components")
@click.option(
    "-t",
    "--theme",
)
@click.pass_context
def list_components(ctx: click.Context, theme: str | None):
    """List available components."""
    if not theme:
        theme: str = config["ckan.base_templates_folder"]

    try:
        info = lib_theme.get_theme(theme)
    except KeyError:
        error_shout(f"Theme {theme} is not recognized")
        raise click.Abort

    ui = info.build_ui(ctx.obj.app._wsgi_app)

    for item in ui:
        click.echo(f"\t{item}")
