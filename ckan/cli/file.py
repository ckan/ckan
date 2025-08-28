from __future__ import annotations

import pydoc
import textwrap
import click


from ckan.common import config
from ckan.config.declaration import Declaration, Key

import ckan.lib.files as lib_files
from . import error_shout


@click.group(short_help="Manage storages and files")
def file(): ...


@file.command()
@click.option(
    "-c", "--with-configuration", is_flag=True, help="Show adapter's configuration"
)
@click.option("-d", "--with-docs", is_flag=True, help="Show adapter's documentation")
@click.option(
    "-a",
    "--show-all",
    is_flag=True,
    help="Show adapters that may be incompatible with CKAN",
)
@click.argument("adapter", required=False)
def adapters(
    adapter: str | None,
    with_docs: bool,
    show_all: bool,
    with_configuration: bool,
):
    """Show all awailable storage adapters."""

    for name in sorted(lib_files.adapters):
        if adapter and name != adapter:
            continue

        item = lib_files.adapters[name]
        if item.hidden:
            continue

        if not show_all and not issubclass(item, lib_files.Storage):
            continue

        click.secho(
            f"{click.style(name, bold=True)} - {item.__module__}:{item.__name__}",
        )

        if with_docs and (doc := pydoc.getdoc(item)):
            doc = f"{click.style('Documentation:', bold=True)}\n{doc}"
            wrapped = textwrap.indent(doc, "\t")
            click.secho(wrapped)
            click.echo()

        if with_configuration and issubclass(item, lib_files.Storage):
            decl = Declaration()
            item.declare_config_options(
                decl, Key.from_string("ckan.files.storage.NAME")
            )
            label = click.style("Configuration:", bold=True)
            configuration = f"{label}\n{decl.into_ini(False, True)}"
            wrapped = textwrap.indent(configuration, "\t")
            click.secho(wrapped)
            click.echo()


@file.group()
def storage():
    """Storage-level operations."""


@storage.command("list")
@click.option("-v", "--verbose", is_flag=True, help="Show storage's details")
def storage_list(verbose: bool):
    """Show all configured storages."""
    for name, settings in lib_files.collect_storage_configuration(config).items():
        click.secho("{}: {}".format(click.style(name, bold=True), settings["type"]))
        if verbose:
            storage = lib_files.get_storage(name)
            click.echo(f"\tSupports: {storage.capabilities}")
            click.echo(f"\tDoes not support: {~storage.capabilities}")


@storage.command("scan")
@click.option("-s", "--storage-name", help="Name of the configured storage")
def storage_scan(storage_name: str | None):
    """Iterate over all files available in storage."""
    try:
        storage = lib_files.get_storage(storage_name)
    except lib_files.exc.UnknownStorageError as err:
        error_shout(err)
        raise click.Abort from err

    try:
        files = storage.scan()
    except lib_files.exc.UnsupportedOperationError as err:
        error_shout(err)
        raise click.Abort from err

    for name in files:
        click.echo(f"* {name}")


@storage.command("transfer")
@click.argument("src")
@click.argument("dest")
@click.option(
    "-l",
    "--location",
    help="Locations of files for transfer",
    multiple=True,
)
@click.option(
    "-r",
    "--remove",
    help="Remove file from the source after transfer",
    is_flag=True,
)
def storage_transfer(src: str, dest: str, location: tuple[str, ...], remove: bool):
    """Move files between storages."""
    from_storage = lib_files.get_storage(src)
    to_storage = lib_files.get_storage(dest)

    is_supported = from_storage.supports_synthetic(
        lib_files.Capability.MOVE if remove else lib_files.Capability.COPY, to_storage
    )

    if not is_supported:
        error_shout("Operation is not supported")
        raise click.Abort

    if not location:
        try:
            location = tuple(from_storage.scan())
        except lib_files.exc.UnsupportedOperationError as err:
            error_shout(err)
            raise click.Abort from err

    op = from_storage.move_synthetic if remove else from_storage.copy_synthetic

    with click.progressbar(location) as bar:
        for item in bar:
            data = lib_files.FileData(lib_files.Location(item))

            try:
                op(data.location, data, to_storage)
            except (
                lib_files.exc.MissingFileError,
                lib_files.exc.ExistingFileError,
            ) as err:
                error_shout(err)
