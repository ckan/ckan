# encoding: utf-8

import click
import magic
import os

from typing import List, Any

from ckan import model
from ckan import logic
from ckan.common import config
from ckan.lib.uploader import get_uploader
from ckan.plugins import plugin_loaded
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
        filepath = upload.old_filepath  # type: ignore
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


@clean.command(
    "activities",
    help="Deletes activities based on a specified date range or offset days.",
)
@click.option(
    "--start_date", type=str, help="The start date in 'YYYY-MM-DD' format."
)
@click.option(
    "--end_date", type=str, help="The end date in 'YYYY-MM-DD' format."
)
@click.option(
    "--offset_days",
    type=str,
    help="Number of days from today. Activities older than this will "
    "be deleted",
)
def activities(start_date: str, end_date: str, offset_days: str):
    """
    Delete activities based on a specified date range or offset days.
    You must provide either a start date and end date or an offset in days.

    Examples:
        ckan clean activities --start_date 2023-01-01 --end_date 2023-01-31
        ckan clean activities --offset_days 30

    """
    if not plugin_loaded("activity"):
        click.secho(
            "Error: The 'activity' plugin is not loaded. "
            "Please add 'activity' to your `ckan.plugins` setting in your "
            "configuration file.",
            fg="red", bold=True
        )
        return

    try:
        site_user = logic.get_action("get_site_user")(
            {"ignore_auth": True}, {}
        )
        context: Context = {"user": site_user["name"]}
        data_dict: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "offset_days": offset_days,
        }

        result = logic.get_action("activity_delete_by_date_range_or_offset")(
            context, data_dict
        )
        click.secho(result["message"], fg="green", bold=True)
    except logic.ValidationError as e:
        click.secho(f"Validation error: {e.error_summary}", fg="red")
