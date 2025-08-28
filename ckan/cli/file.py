from __future__ import annotations

import pydoc
import textwrap
import click
import file_keeper as fk
import sqlalchemy as sa
from ckan import model, logic
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

            label = click.style("Supports", fg="green", bold=True)
            click.secho(f"\t{label}: {storage.capabilities}")

            label = click.style("Does not support", fg="red", bold=True)
            click.secho(f"\t{label}: {~storage.capabilities}")


@storage.command("scan")
@click.option("-s", "--storage-name", help="Name of the configured storage")
@click.option(
    "--unknown-mark",
    help="Mark unknown files with specified symbol",
    default="❓",
)
@click.option(
    "--known-mark",
    help="Mark known files with specified symbol",
    default="✅",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Show file details. Repeat to include details of unknown files",
)
@click.option(
    "-u",
    "--unknown-only",
    is_flag=True,
    help="Show only unknown files, that are not registered in DB",
)
def storage_scan(
    storage_name: str | None,
    known_mark: str,
    unknown_mark: str,
    verbose: int,
    unknown_only: bool,
):
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
        file = model.Session.scalar(model.File.by_location(name, storage.settings.name))
        if unknown_only and file:
            continue

        mark = known_mark if file else unknown_mark
        click.echo(f"{mark} {name}")
        if verbose:
            if file:
                info = file

            elif verbose > 1 and storage.supports(lib_files.Capability.ANALYZE):
                info = storage.analyze(lib_files.Location(name))

            else:
                info = None

            if info:
                click.echo(f"\tSize: {fk.humanize_filesize(info.size)}")
                click.echo(f"\tMIME Type: {info.content_type}")
                click.echo(f"\tContent hash: {info.hash}")


@storage.command("transfer")
@click.argument("src")
@click.argument("dest")
@click.option(
    "-i",
    "--id",
    help="IDs of files for transfer",
    multiple=True,
)
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
def storage_transfer(
    src: str, dest: str, location: tuple[str, ...], id: tuple[str, ...], remove: bool
):
    """Move files between storages.

    Files that are not registered in DB are simply moved between
    storages. Files that has correspoinding record in database got their
    fields, including ``storage``, updated as if file was directly uploaded
    into the target storage.
    """
    from_storage = lib_files.get_storage(src)
    to_storage = lib_files.get_storage(dest)

    if remove and from_storage.supports_synthetic(
        lib_files.Capability.MOVE, to_storage
    ):
        op = from_storage.move_synthetic

    elif not remove and from_storage.supports_synthetic(
        lib_files.Capability.COPY, to_storage
    ):
        op = from_storage.copy_synthetic

    else:
        error_shout("Operation is not supported")
        raise click.Abort

    # normalize IDs to locations to process all files in the same way instead
    # of writing two separate routes for IDs and locations
    extra_locations = model.Session.scalars(
        sa.select(model.File.location).where(
            model.File.storage == src, model.File.id.in_(id)
        )
    )
    targets = set()
    targets.update(location)
    targets.update(extra_locations.all())

    if not targets:
        try:
            targets = tuple(from_storage.scan())
        except lib_files.exc.UnsupportedOperationError as err:
            error_shout(err)
            raise click.Abort from err

    with click.progressbar(targets) as bar:
        for item in bar:
            data = lib_files.FileData(lib_files.Location(item))

            try:
                info = op(data.location, data, to_storage)

            except (
                lib_files.exc.MissingFileError,
                lib_files.exc.ExistingFileError,
            ) as err:
                error_shout(err)

            else:
                if file := model.Session.scalar(model.File.by_location(item, src)):
                    info.into_object(file)
                    file.storage = dest
                    model.Session.commit()
