import click
from datetime import datetime
from typing import Any

from ckan.cli.clean import clean
from ckan import model, logic, types


@clean.command(
    "activities",
    help="Deletes activities based on a specified date range or offset days.",
)
@click.option(
    "--start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="The start date in 'YYYY-MM-DD' format.",
)
@click.option(
    "--end_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="The end date in 'YYYY-MM-DD' format.",
)
@click.option(
    "--offset_days",
    type=click.INT,
    help="Number of days from today. Activities older than this will "
    "be deleted",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="If set, do not prompt for confirmation before deleting activities.",
)
def activities(
    start_date: datetime, end_date: datetime, offset_days: int, quiet: bool
):
    """
    Delete activities based on a specified date range or offset days.
    You must provide either a start date and end date or an offset in days.

    Examples:
        ckan clean activities --start_date 2023-01-01 --end_date 2023-01-31
        ckan clean activities --offset_days 30

    """
    try:
        site_user = logic.get_action("get_site_user")(
            {"ignore_auth": True}, {}
        )
        context: types.Context = {
            "user": site_user["name"],
            "defer_commit": not quiet,
        }
        data_dict: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "offset_days": offset_days,
        }

        result = logic.get_action("activity_delete")(context, data_dict)[
            "message"
        ]

        if not quiet:
            confirm_text = (
                f"Are you sure you want to delete {result} activities? "
                "This action cannot be undone."
            )
            if click.confirm(confirm_text, default=False, abort=True):
                click.secho(
                    f"Deleted {result} rows from the activity table.",
                    fg="green",
                    bold=True,
                )
                model.Session.commit()
            else:
                click.secho("Operation cancelled.", fg="yellow")

        else:
            click.secho(result, fg="green", bold=True)
    except logic.ValidationError as e:
        click.secho(f"Validation error: {e.error_summary}", fg="red")
