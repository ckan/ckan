from __future__ import annotations

import logging
import os

from typing import Any, cast

import click

from ckan.common import config
from ckan.lib import theme as lib_theme


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
        click.echo(f"\tPath: {info['path']}")

        lineage = []
        parent = info.get("extends")
        while parent:
            if parent_info := themes.get(parent):
                lineage.append(parent)
                parent = parent_info.get("extends")
            else:
                lineage.append(click.style(parent, fg="red"))

        if lineage:

            click.secho(f"\tExtends: {' -> '.join(lineage)}")
