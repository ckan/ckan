# encoding: utf-8

import click
import magic
import os

from ckan import model
from ckan import logic
from ckan.common import config
from ckan.lib.uploader import get_uploader


@click.group(short_help="Provide commands to clean entities from the database")
@click.help_option("-h", "--help")
def clean():
    pass


def _get_users_with_invalid_image(mimetypes):
    """Returns a list of users containing images with mimetypes not supported.
    """
    users = model.User.all()
    users_with_img = [u for u in users if u.image_url]
    invalid = []
    for user in users_with_img:
        upload = get_uploader("user", old_filename=user.image_url)
        filepath = upload.old_filepath
        if os.path.exists(filepath):
            mimetype = magic.from_file(filepath, mime=True)
            if mimetype not in mimetypes:
                invalid.append(user)
    return invalid


@clean.command("users", short_help="Clean users containing invalid images.")
@click.option(
    "-f", "--force", is_flag=True, help="Do not ask for comfirmation."
)
def users(force):
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
    context = {"user": site_user["name"]}

    for user in invalid:
        upload = get_uploader("user", old_filename=user.image_url)
        file_path = upload.old_filepath  # type: ignore
        try:
            os.remove(file_path)
        except Exception:
            msg = "Cannot remove {}. User will not be deleted.".format(
                file_path
            )
            click.echo(msg)
        else:
            logic.get_action("user_delete")(context, {"id": user.name})
            click.secho("Deleted user: %s" % user.name, fg="green", bold=True)
