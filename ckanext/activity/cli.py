import click
from datetime import datetime
from typing import Any

from ckan.cli.clean import clean
from ckan import logic, types

# ISO 8601 date and datetime formats (date-only and with time)
_DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]

# Batch size for activity deletion (avoids timeouts on large tables)
_DEFAULT_BATCH_SIZE = 50_000


@clean.command(
    "activities",
    help="Deletes activities based on a specified date range or offset days.",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=_DATE_FORMATS),
    help="Start of range (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:mm).",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=_DATE_FORMATS),
    help="End of range (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:mm).",
)
@click.option(
    "--offset-days",
    type=click.INT,
    help="Number of days from today. Activities older than this will "
    "be deleted",
)
@click.option(
    "--keep",
    type=click.INT,
    default=None,
    help="Keep this many most recent activities per item (object); "
    "only older ones in the range are deleted.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Do not ask for confirmation.",
)
def activities(
    start_date: datetime,
    end_date: datetime,
    offset_days: int,
    keep: int | None,
    force: bool,
):
    """
    Delete activities based on a specified date range or offset days.
    Activities are always processed in batches to avoid timeouts on large tables.
    You must provide either a start date and end date or an offset in days.
    Use --keep N to retain the N most recent activities per item.

    Examples:
        ckan clean activities --start-date 2023-01-01 --end-date 2023-01-31
        ckan clean activities --offset-days 30
        ckan clean activities --offset-days 90 --keep 5
        ckan clean activities --offset-days 300 -f

    """
    try:
        if not force:
            if not click.confirm(
                "This will delete matching activities in batches. "
                "This action cannot be undone. Continue?",
                default=False,
                abort=True,
            ):
                click.secho("Operation cancelled.", fg="yellow")
                return

        site_user = logic.get_action("get_site_user")(
            {"ignore_auth": True}, {}
        )
        context: types.Context = {
            "user": site_user["name"],
        }
        data_dict: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "offset_days": offset_days,
            "keep": keep,
            "batch_size": _DEFAULT_BATCH_SIZE,
        }

        result = logic.get_action("activity_delete")(context, data_dict)[
            "message"
        ]
        click.secho(result, fg="green", bold=True)
    except logic.ValidationError as e:
        click.secho(f"Validation error: {e.error_summary}", fg="red")
