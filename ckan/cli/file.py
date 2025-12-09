from __future__ import annotations

import os
import pydoc
import sys
import textwrap
from datetime import datetime, timezone
from typing import IO, cast

import click
import file_keeper as fk
import sqlalchemy as sa
from babel.dates import format_datetime, format_timedelta
from werkzeug.utils import secure_filename

from ckan import logic, model
from ckan.common import config
from ckan.config.declaration import Declaration, Key
from ckan.lib import files

from . import error_shout

storage_option = click.option(
    "-s", "--storage-name", help="Name of the configured storage"
)


def _now():
    return datetime.now(timezone.utc)


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
    """Show all available storage adapters."""

    for name in sorted(files.adapters):
        if adapter and name != adapter:
            continue

        item = files.adapters[name]
        if item.hidden:
            continue

        if not show_all and not issubclass(item, files.Storage):
            continue

        click.secho(
            f"{click.style(name, bold=True)} - {item.__module__}:{item.__name__}",
        )

        if with_docs and (doc := pydoc.getdoc(item)):
            doc = f"{click.style('Documentation:', bold=True)}\n{doc}"
            wrapped = textwrap.indent(doc, "\t")
            click.secho(wrapped)
            click.echo()

        if with_configuration and issubclass(item, files.Storage):
            decl = Declaration()
            item.declare_config_options(
                decl, Key.from_string("ckan.files.storage.NAME")
            )
            label = click.style("Configuration:", bold=True)
            configuration = f"{label}\n{decl.into_ini(False, True)}"
            wrapped = textwrap.indent(configuration, "\t")
            click.secho(wrapped)
            click.echo()


@file.command("stream")
@click.argument("file_id")
@click.option(
    "--offset", type=int, default=0, help="Start streaming from specified byte offset"
)
@click.option("--length", type=int, help="Number of bytes to stream")
@click.option("-o", "--output", help="Stream into specified file or directory")
def file_stream(  # noqa: C901
    file_id: str,
    output: str | None,
    offset: int,
    length: int | None,
):
    """Stream content of the file."""
    file_obj = model.Session.get(model.File, file_id)
    if not file_obj:
        error_shout("File not found")
        raise click.Abort

    try:
        storage = files.get_storage(file_obj.storage)
    except files.exc.UnknownStorageError as err:
        error_shout(err)
        raise click.Abort from err

    file_data = files.FileData.from_object(file_obj)
    if length is None:
        # stream to the end of file
        end = None
    else:
        end = offset + length

    if not offset and end is None and storage.supports(files.Capability.STREAM):
        content_stream = storage.stream(file_data)

    elif storage.supports(files.Capability.RANGE):
        content_stream = storage.range(file_data, offset, end)

    elif storage.supports_synthetic(files.Capability.RANGE, storage):
        content_stream = storage.range_synthetic(file_data, offset, end)

    else:
        error_shout("File streaming is not supported")
        raise click.Abort

    if output is None:
        dest: IO[bytes] = sys.stdout.buffer

    else:
        if os.path.isdir(output):
            # stream into the specified directory with original filename. But
            # make sure the name is sanitized, as we don't control it
            output = os.path.join(output, secure_filename(file_obj.name))
        try:
            dest = open(output, "xb")  # noqa: SIM115
        except FileExistsError:
            error_shout(f"Output file '{output}' already exists")
            raise click.Abort

    for chunk in content_stream:
        dest.write(chunk)


@file.group()
def storage():
    """Storage-level operations."""


@storage.command("list")
@click.option("-v", "--verbose", is_flag=True, help="Show storage's details")
def storage_list(verbose: bool):
    """Show all configured storages."""
    for name, settings in files.collect_storage_configuration(config).items():
        click.secho("{}: {}".format(click.style(name, bold=True), settings["type"]))
        if verbose:
            storage_obj = files.get_storage(name)

            label = click.style("Supports", fg="green", bold=True)
            click.secho(f"\t{label}: {storage_obj.capabilities}")

            label = click.style("Does not support", fg="red", bold=True)
            click.secho(f"\t{label}: {~storage_obj.capabilities}")


@storage.command("scan")
@storage_option
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
    storage_name = cast(
        str, storage_name or config["ckan.files.default_storages.default"]
    )

    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError as err:
        error_shout(err)
        raise click.Abort from err

    try:
        names = storage.scan()
    except files.exc.UnsupportedOperationError as err:
        error_shout(err)
        raise click.Abort from err

    for name in names:
        file = model.Session.scalar(model.File.by_location(name, storage_name))
        if unknown_only and file:
            continue

        mark = known_mark if file else unknown_mark
        click.echo(f"{mark} {name}")
        if verbose:
            if file:
                info = file

            elif verbose > 1 and storage.supports(files.Capability.ANALYZE):
                info = storage.analyze(files.Location(name))

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
@click.option(
    "--skip-missing-files", is_flag=True, help="Do not interrupt on missing files"
)
@click.option(
    "--skip-existing-files", is_flag=True, help="Do not interrupt on existing files"
)
def storage_transfer(  # noqa: C901
    src: str,
    dest: str,
    location: tuple[str, ...],
    id: tuple[str, ...],
    remove: bool,
    skip_existing_files: bool,
    skip_missing_files: bool,
):
    """Move files between storages.

    Files that are not registered in DB are simply moved between
    storages. Files that has correspoinding record in database got their
    fields, including ``storage``, updated as if file was directly uploaded
    into the target storage.
    """
    from_storage = files.get_storage(src)
    to_storage = files.get_storage(dest)

    if remove and from_storage.supports_synthetic(files.Capability.MOVE, to_storage):
        op = from_storage.move_synthetic

    elif not remove and from_storage.supports_synthetic(
        files.Capability.COPY, to_storage
    ):
        op = from_storage.copy_synthetic

    else:
        error_shout(f"Operation is not supported by the storage {src}")
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
        except files.exc.UnsupportedOperationError as err:
            error_shout(err)
            raise click.Abort from err

    with click.progressbar(targets) as bar:
        for item in bar:
            data = files.FileData(files.Location(item))

            try:
                info = op(data.location, data, to_storage)

            except files.exc.MissingFileError as err:
                error_shout(err)
                if not skip_missing_files:
                    raise click.Abort

            except files.exc.ExistingFileError as err:
                error_shout(err)
                if not skip_existing_files:
                    raise click.Abort

            else:
                if file := model.Session.scalar(model.File.by_location(item, src)):
                    info.into_object(file)
                    file.storage = dest
                    model.Session.commit()


@storage.command("clean")
@storage_option
@click.option("--remove-registered", help="", is_flag=True)
@click.option("--remove-unknown", help="", is_flag=True)
def storage_clean(
    storage_name: str | None, remove_registered: bool, remove_unknown: bool
):
    """Remove all files from the storage."""
    user = logic.get_action("get_site_user")({"ignore_auth": True}, {})
    storage_name = storage_name or config["ckan.files.default_storages.default"]
    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError as err:
        error_shout(err)
        raise click.Abort from err

    stmt = sa.select(model.File.id).where(model.File.storage == storage_name)

    total = model.Session.scalar(stmt.with_only_columns(sa.func.count()))

    if total:
        click.echo(f"Storage {storage_name} contains {total} registered files.")

        if remove_registered:
            bar = click.progressbar(model.Session.scalars(stmt), length=total)
            with bar:
                for id in bar:
                    bar.label = f"Removing {id}"
                    logic.get_action("file_delete")({"user": user["name"]}, {"id": id})

        else:
            click.echo(
                "Skipping registered files removal."
                + " Enable with `--remove-registered` flag"
            )

    if storage.supports(files.Capability.SCAN) and (names := list(storage.scan())):
        click.echo(f"Storage {storage_name} contains {len(names)} unknown files.")

        if remove_unknown:
            bar = click.progressbar(names)
            with bar:
                for name in bar:
                    bar.label = f"Removing {name}"
                    storage.remove(files.FileData(files.Location(name)))

        else:
            click.echo(
                "Skipping unknown files removal."
                + " Enable with `--remove-unknown` flag"
            )


@file.group()
def stats():
    """Storage statistics."""


@stats.command("overview")
@storage_option
def stats_overview(storage_name: str | None):
    """General information about storage usage.

    Computed using registered files. If storage contains files without
    corresponding DB record, they won't be added to these numbers.
    """
    storage_name = storage_name or config["ckan.files.default_storages.default"]
    try:
        files.get_storage(storage_name)
    except files.exc.UnknownStorageError as err:
        error_shout(f"Storage {storage_name} is not configured")
        raise click.Abort from err

    stmt = sa.select(
        sa.func.sum(model.File.size),
        sa.func.count(model.File.id),
        sa.func.max(model.File.ctime),
        sa.func.min(model.File.ctime),
    ).where(model.File.storage == storage_name)
    row = model.Session.execute(stmt).fetchone()
    size, count, newest, oldest = row if row else (0, 0, _now(), _now())

    if not count:
        error_shout(f"Storage {storage_name} is empty")
        return

    click.secho(f"Number of files: {click.style(count, bold=True)}")
    click.secho(
        f"Used space: {click.style(fk.humanize_filesize(size), bold=True)}",
    )
    click.secho(
        "Newest file created at: "
        + f"{click.style(format_datetime(newest), bold=True)} "
        + f"({format_timedelta(newest - _now(), add_direction=True)})",
    )
    click.secho(
        "Oldest file created at: "
        + f"{click.style(format_datetime(oldest), bold=True)} "
        + f"({format_timedelta(oldest - _now(), add_direction=True)})",
    )


@stats.command("types")
@storage_option
def stats_types(storage_name: str | None):
    """Files distribution by MIME type."""
    storage_name = storage_name or config["ckan.files.default_storages.default"]
    stmt = (
        sa.select(
            model.File.content_type,
            sa.func.count(model.File.content_type).label("count"),
        )
        .where(model.File.storage == storage_name)
        .group_by(model.File.content_type)
        .order_by(model.File.content_type)
    )

    total = model.Session.scalar(sa.select(sa.func.sum(stmt.c.count)))
    click.secho(
        f"Storage {click.style(storage_name, bold=True)} contains "
        + f"{click.style(total, bold=True)} files",
    )
    for content_type, count in model.Session.execute(stmt):
        click.secho(f"\t{content_type}: {click.style(count, bold=True)}")


@stats.command("owner")
@storage_option
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show distribution for every owner ID",
)
def stats_owner(storage_name: str | None, verbose: bool):
    """Files distribution by owner."""
    storage_name = storage_name or config["ckan.files.default_storages.default"]
    owner_col = (
        sa.func.concat(model.Owner.owner_type, " ", model.Owner.owner_id)
        if verbose
        else sa.func.concat(model.Owner.owner_type, "")
    )

    stmt = (
        sa.select(
            owner_col.label("owner"),
            sa.func.count(model.File.id),
        )
        .where(model.File.storage == storage_name)
        .outerjoin(
            model.Owner,
            sa.and_(
                model.Owner.item_id == model.File.id,
                model.Owner.item_type == "file",
            ),
        )
        .group_by(owner_col)
    ).order_by(owner_col)

    total = model.Session.scalar(sa.select(sa.func.sum(stmt.c.count)))
    click.secho(
        f"Storage {click.style(storage_name, bold=True)} contains "
        + f"{click.style(total, bold=True)} files",
    )
    for owner, count in model.Session.execute(stmt):
        clean_owner = owner.strip() or click.style(
            "has no owner",
            underline=True,
            bold=True,
        )
        click.secho(
            f"\t{clean_owner}: {click.style(count, bold=True)}",
        )


@file.group()
def maintain():
    """Storage maintenance."""


@maintain.command()
@storage_option
@click.option("--remove", is_flag=True, help="Remove files")
def empty_owner(storage_name: str | None, remove: bool):
    """Manage files that have no owner."""
    storage_name = storage_name or config["ckan.files.default_storages.default"]
    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError as err:
        error_shout(err)
        raise click.Abort from err

    if remove and not storage.supports(files.Capability.REMOVE):
        error_shout(f"Storage {storage_name} does not support file removal")
        raise click.Abort

    stmt = (
        sa.select(model.File)
        .outerjoin(model.File.owner)
        .where(model.File.storage == storage_name, model.Owner.owner_id.is_(None))
    )

    total = model.Session.scalar(stmt.with_only_columns(sa.func.count()))
    if not total:
        click.echo(f"Every file in storage {storage_name} has owner reference")
        return

    click.echo("Following files do not have owner reference:")

    for file in model.Session.scalars(stmt):
        size = fk.humanize_filesize(file.size)
        click.echo(f"\t{file.id}: {file.name} [{file.content_type}, {size}]")

    if not remove:
        click.echo("To remove these files, rerun with `--remove` option enabled")
        return

    action = logic.get_action("file_delete")

    with click.progressbar(model.Session.scalars(stmt), length=total) as bar:
        for file in bar:
            action({"ignore_auth": True}, {"id": file.id})


@maintain.command()
@storage_option
@click.option("--remove", is_flag=True, help="Remove files")
def missing_files(storage_name: str | None, remove: bool):
    """Manage files that do not exist in storage."""
    storage_name = storage_name or config["ckan.files.default_storages.default"]
    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError as err:
        error_shout(err)
        raise click.Abort from err

    if not storage.supports(files.Capability.EXISTS):
        error_shout(
            f"Storage {storage_name} does not support file availability checks",
        )
        raise click.Abort

    if remove and not storage.supports(files.Capability.REMOVE):
        error_shout(f"Storage {storage_name} does not support file removal")
        raise click.Abort

    stmt = sa.select(model.File).where(model.File.storage == storage_name)
    total = model.Session.scalar(stmt.with_only_columns(sa.func.count()))
    missing: list[model.File] = []
    with click.progressbar(model.Session.scalars(stmt), length=total) as bar:
        for file in bar:
            data = files.FileData.from_object(file)
            if not storage.exists(data):
                missing.append(file)

    if not missing:
        click.echo(
            f"No missing files located in storage {storage_name}",
        )
        return

    click.echo(f"Following files are not found in the storage {storage_name}")
    for file in missing:
        size = fk.humanize_filesize(file.size)
        click.echo(
            f"\t{file.id}: {file.name} [{file.content_type}, {size}]",
        )

    if not remove:
        click.echo("To remove these files, rerun with `--remove` option enabled")
        return

    action = logic.get_action("file_delete")

    with click.progressbar(missing) as bar:
        for file in bar:
            action({"ignore_auth": True}, {"id": file.id})
