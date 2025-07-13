from __future__ import annotations

import pydoc
import textwrap
import click

from ckan.common import config
from ckan.config.declaration import Declaration, Key

import ckan.lib.files as lib_files


@click.group(short_help="Manage storages and files")
def files(): ...


@files.command()
@click.option(
    "-c", "--with-configuration", is_flag=True, help="Show adapter's configuration"
)
@click.option("-d", "--with-docs", is_flag=True, help="Show adapter's documentation")
@click.option("-H", "--include-hidden", is_flag=True, help="Show hidden adapters")
@click.argument("adapter", required=False)
def adapters(
    adapter: str | None,
    with_docs: bool,
    include_hidden: bool,
    with_configuration: bool,
):
    """Show all awailable storage adapters."""

    for name in sorted(lib_files.adapters):
        if adapter and name != adapter:
            continue

        item = lib_files.adapters[name]
        if item.hidden and not include_hidden:
            continue

        click.secho(
            f"{click.style(name, bold=True)} - {item.__module__}:{item.__name__}",
        )

        if with_docs and (doc := pydoc.getdoc(item)):
            doc = f"{click.style('Documentation:', bold=True)}\n{doc}"
            wrapped = textwrap.indent(doc, "\t")
            click.secho(wrapped)
            click.echo()

        if with_configuration:
            decl = Declaration()
            item.declare_config_options(
                decl, Key.from_string("ckan.files.storage.NAME")
            )
            configuration = f"{click.style('Configuration:', bold=True)}\n{decl.into_ini(False, True)}"
            wrapped = textwrap.indent(configuration, "\t")
            click.secho(wrapped)
            click.echo()


@files.group()
def storage():
    """Storage-level operations."""


@storage.command("list")
@click.option("-v", "--verbose", is_flag=True, help="Show storage's details")
def storages_list(verbose: bool):
    """Show all configured storages."""
    for name, settings in lib_files.collect_storage_configuration(config).items():
        click.secho("{}: {}".format(click.style(name, bold=True), settings["type"]))
        if verbose:
            storage = lib_files.get_storage(name)
            click.echo(f"\tSupports: {storage.capabilities}")
            click.echo(f"\tDoes not support: {~storage.capabilities}")
