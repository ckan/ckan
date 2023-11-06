import click
from typing import Optional
import datetime

from ckan.lib.plugins import plugin_validate
from ckanext.activity import utils
from ckanext.activity.logic.schema import delete_activity_rows_schema


@click.group(short_help="Activity management commands.")
def activity():
    """Activity management commands.
    """
    pass


@activity.command(short_help="Delete rows from the activity table.")
@click.option(
    "-i", "--id", help="Only delete activities for this object ID."
)
@click.option(
    "-l", "--limit", help="Limit the number of activities deleted.", type=int
)
@click.option(
    "-o", "--offset", help="Offset the number of activities deleted.", type=int
)
@click.option(
    "-t", "--activity-types", multiple=True,
    help="Only delete activities of these types. Accepts multiple."
)
@click.option(
    "-T", "--exclude-activity-types", multiple=True,
    help="Do not delete activities of these types. Accepts multiple."
)
@click.option(
    "-b", "--before",
    help="Delete activities `before` a Unix timestamp.", type=float
)
@click.option(
    "-a", "--after",
    help="Delete activities `after` a Unix timestamp.", type=float
)
@click.option(
    "-d", "--days", help="Delete activities before x `days` ago.", type=int
)
@click.option(
    "-q", "--quiet", is_flag=True, help="Supresses human interaction."
)
def delete(id: Optional[str],
           limit: Optional[int],
           offset: Optional[int],
           activity_types: Optional[tuple[str]],
           exclude_activity_types: Optional[tuple[str]],
           before: Optional[float],
           after: Optional[float],
           days: Optional[int],
           quiet: Optional[bool]):
    """Delete rows from the activity table.

    Example:

        ckan activity delete -b 1699041313\n
        ckan activity delete -d 90 -q\n
        ckan activity delete --id=7e608e4c-c332-4511-ad43-97eb59cb5bd1
                             --offset=100 --limit=50

    """
    if days:
        before = (datetime.datetime.today()
                  - datetime.timedelta(days=float(days))).timestamp()

    data_dict = {
        "id": id,
        "limit": limit,
        "offset": offset,
        "activity_types": list(activity_types) \
            if activity_types else [],
        "exclude_activity_types": list(exclude_activity_types) \
            if exclude_activity_types else [],
        "before": before,
        "after": after,
    }

    data, errors = plugin_validate(None, {}, data_dict,
                                   delete_activity_rows_schema(),
                                   'activity_delete')

    if errors:
        for key, errors in errors.items():
            for message in errors:
                click.echo(f"{key}: {message}")
        return

    activity_count = utils.get_activity_count(data)

    if not bool(activity_count):
        click.echo("No activities found.")
        return

    if not quiet:
        click.confirm(
            f"Are you sure you want to delete {activity_count} activities?",
            abort=True)

    utils.delete_activities(data)

    click.echo(f"Deleted {activity_count} rows from the activity table.")
