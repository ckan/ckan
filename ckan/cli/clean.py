from __future__ import annotations

import magic
import os
import click

from ckan import model
from ckan import logic
from ckan.common import config
from ckan.lib import files
from ckan.lib.uploader import get_uploader, FkUpload
from ckan.types import Context


@click.group(short_help="Provide commands to clean entities from the database")
@click.help_option("-h", "--help")
def clean():
    pass


def _get_users_with_invalid_image() -> list[model.User]:
    """Returns a list of users containing images with mimetypes not supported.
    """
    users = model.User.all()
    users_with_img = [u for u in users if u.image_url]
    invalid = []

    for user in users_with_img:
        upload = get_uploader("user", old_filename=user.image_url)
        if isinstance(upload, FkUpload):
            filename = upload.old_filename
            storage = upload.storage
            if not isinstance(storage, files.Storage) or not filename:
                continue
            location = files.Location(filename)
            if storage.exists(files.FileData.from_string(location)):
                content_type = storage.content_type(location)
                try:
                    storage.validate_content_type(content_type)
                except files.exc.WrongUploadTypeError:
                    invalid.append(user)
        else:
            mimetypes = config["ckan.upload.user.mimetypes"]
            filepath = upload.old_filepath  # pyright: ignore[reportAttributeAccessIssue]
            if os.path.exists(filepath):
                mimetype = magic.from_file(filepath, mime=True)
                if mimetype not in mimetypes:
                    invalid.append(user)

    return invalid


@clean.command("users", short_help="Clean users containing invalid images.")
@click.option(
    "-f", "--force", is_flag=True, help="Do not ask for confirmation."
)
def users(force: bool):
    """Removes users with invalid images from the database.

    Invalid images are the ones with mimetypes not defined in
    `ckan.upload.user.mimetypes` configuration option.

    This command will work only for CKAN's default Upload, other
    extensions defining upload interfaces will need to implement its
    own logic to retrieve and determine if an uploaded image contains
    an invalid mimetype.

    Example:

      ckan clean users
      ckan clean users --force

    """
    invalid = _get_users_with_invalid_image()

    if not invalid:
        click.echo("No users were found with invalid images.")
        return

    for user in invalid:
        msg = "User {} has an invalid image: {}".format(
            user.name, user.image_url
        )
        click.echo(msg)

    if not force:
        click.confirm("Permanently delete users and their images?", abort=True)

    site_user = logic.get_action("get_site_user")({"ignore_auth": True}, {})
    context: Context = {"user": site_user["name"]}

    for user in invalid:
        upload = get_uploader("user", old_filename=user.image_url)
        filename = upload.old_filename  # type: ignore

        storage: files.Storage = upload.storage  # type: ignore
        try:
            storage.remove(
                files.FileData(files.Location(filename))
            )

        except files.exc.UnsupportedOperationError as err:
            # file cannot be removed. Maybe it still possible to remove the
            # user, but because files are not tracked yet, there will be no way
            # to identify orphaned files in future. So, let's keep user for now
            click.echo(str(err))
            msg = "Cannot remove {}. User will not be deleted.".format(
                filename
            )
            click.echo(msg)
            continue

        logic.get_action("user_delete")(context, {"id": user.name})
        click.secho("Deleted user: %s" % user.name, fg="green", bold=True)
