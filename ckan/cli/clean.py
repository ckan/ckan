# encoding: utf-8

import click
import magic
import os

from typing import List

from ckan import model
from ckan import logic
from ckan.common import config
from ckan.lib import files
from ckan.lib.uploader import get_uploader
from ckan.types import Context


@click.group(short_help="Provide commands to clean entities from the database")
@click.help_option("-h", "--help")
def clean():
    pass


def _get_users_with_invalid_image(mimetypes: List[str]) -> List[model.User]:
    """Returns a list of users containing images with mimetypes not supported.
    """
    users = model.User.all()
    users_with_img = [u for u in users if u.image_url]
    invalid = []
    for user in users_with_img:
        upload = get_uploader("user", old_filename=user.image_url)
        filename = upload.old_filename  # type: ignore

        storage: files.Storage = upload.storage  # type: ignore
        location = files.Location(filename)
        if storage.exists(files.FileData(location)):
            info = storage.analyze(location)
            if info.content_type not in mimetypes:
                invalid.append(user)
    return invalid


@clean.command("users", short_help="Clean users containing invalid images.")
@click.option(
    "-f", "--force", is_flag=True, help="Do not ask for comfirmation."
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
    mimetypes = config.get("ckan.upload.user.mimetypes")
    if not mimetypes:
        click.echo("No mimetypes have been configured for user uploads.")
        return

    invalid = _get_users_with_invalid_image(mimetypes)

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

        except files.exc.MissingFileError as err:
            # file does not exist and we can continue with user removal
            click.echo(str(err))

        except files.exc.UnsupportedOperationError as err:
            # file cannot be removed. Maybe it still possible to remove the
            # user, but because files are not tracked yet, there will be no way
            # to identify orphaned files in future. So, let's keep user for now
            click.echo(str(err))
            continue

        except Exception:
            msg = "Cannot remove {}. User will not be deleted.".format(
                filename
            )
            click.echo(msg)
            continue

        logic.get_action("user_delete")(context, {"id": user.name})
        click.secho("Deleted user: %s" % user.name, fg="green", bold=True)
