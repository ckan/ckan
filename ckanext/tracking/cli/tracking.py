# encoding: utf-8

import datetime
import csv

from typing import NamedTuple, Optional

import re
import click
import sqlalchemy as sa
from sqlalchemy import desc, func, select, cast
from sqlalchemy.orm import aliased

from ckan.model import Package
from ckan.model.meta import Session as session
import ckan.logic as logic
from ckan.cli import error_shout
from ckan.common import config

from ckanext.tracking.model import (TrackingSummary as ts,
                                    TrackingRaw as tr)


class ViewCount(NamedTuple):
    id: str
    name: str
    count: int


@click.group(name="tracking", short_help="Update tracking statistics")
def tracking():
    pass


@tracking.command()
@click.argument("start_date", required=False)
def update(start_date: Optional[str]):
    update_all(start_date)


@tracking.command()
@click.argument("output_file", type=click.Path())
@click.argument("start_date", required=False)
def export(output_file: str, start_date: Optional[str]):
    update_all(start_date)
    export_tracking(output_file)


def update_all(start_date: Optional[str] = None):
    if start_date:
        date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # No date given. See when we last have data for and get data
        # from 2 days before then in case new data is available.
        # If no date here then use 2011-01-01 as the start date
        stmt = select(ts).order_by(ts.tracking_date.desc())
        result = session.scalars(stmt).first()
        if result:
            date = result.tracking_date
            date += datetime.timedelta(-2)
            # convert date to datetime
            combine = datetime.datetime.combine
            date = combine(date, datetime.time(0))
        else:
            date = datetime.datetime(2011, 1, 1)
    start_date_solrsync = date
    end_date = datetime.datetime.now()

    while date < end_date:
        stop_date = date + datetime.timedelta(1)
        update_tracking(date)
        click.echo("tracking updated for {}".format(date))
        date = stop_date

    update_tracking_solr(start_date_solrsync)


def _total_views():
    '''
    Total views for each package
    '''
    stmt = (
        select(
            ts.package_id,
            func.coalesce(func.sum(ts.count), 0).label("total_views"),
        )
        .group_by(ts.package_id)
        .order_by(desc("total_views"))
    )

    return [ViewCount(*t) for t in session.execute(stmt)]


def _recent_views(measure_from: datetime.date):
    '''
    Recent views for each package
    '''
    stmt = (
        select(
            ts.package_id,
            func.coalesce(func.sum(ts.count), 0).label("total_views"),
        )
        .where(ts.tracking_date >= measure_from)
        .group_by(ts.package_id)
        .order_by(desc("total_views"))
    )
    return [
        ViewCount(*t) for t in session.execute(stmt)
    ]  # {'from': measure_from})


def export_tracking(output_filename: str):
    '''
    Write tracking summary to a csv file.
    '''
    headings = [
        "dataset id",
        "dataset name",
        "total views",
        "recent views (last 2 weeks)",
    ]

    measure_from = datetime.date.today() - datetime.timedelta(days=14)
    recent_views = _recent_views(measure_from)
    total_views = _total_views()

    with open(output_filename, "w") as fh:
        f_out = csv.writer(fh)
        f_out.writerow(headings)
        recent_views_for_id = dict((r.id, r.count) for r in recent_views)
        f_out.writerows(
            [
                (r.id, r.name, r.count, recent_views_for_id.get(r.id, 0))
                for r in total_views
            ]
        )


def update_tracking(summary_date: datetime.datetime):
    '''
    Update the tracking_summary table with data from tracking_raw
    '''
    package_url = "/dataset/"
    rp = config.get('ckan.root_path', '')
    root_path = re.sub('/{{LANG}}', '', rp) if rp else ''
    url = (
        func.replace(tr.url, root_path, '').label("tracking_url")
        if root_path else tr.url
    )
    session.query(ts).filter(ts.tracking_date == summary_date).delete()
    tracking_tmp = (
        session.query(
            url,
            tr.user_key,
            cast(tr.access_timestamp, sa.Date)
            .label("tracking_date"),
            tr.tracking_type,
        )
        .filter(cast(tr.access_timestamp,
                     sa.Date) == summary_date)
        .distinct()
        .subquery()
    )
    summary = session.query(
        tracking_tmp.c.tracking_url if root_path else tracking_tmp.c.url,
        tracking_tmp.c.tracking_date,
        tracking_tmp.c.tracking_type,
        func.count(tracking_tmp.c.user_key).label("count"),
    ).group_by(
        tracking_tmp.c.tracking_url if root_path else tracking_tmp.c.url,
        tracking_tmp.c.tracking_date,
        tracking_tmp.c.tracking_type,
    )
    for tracking_url, tracking_date, tracking_type, count in summary:
        summary_row = ts(
            url=tracking_url,
            count=count,
            tracking_date=tracking_date,
            tracking_type=tracking_type,
            package_id=None,
            running_total=0,
            recent_views=0,
        )
        session.add(summary_row)
    session.commit()
    update_tracking_summary_with_package_id(package_url)


def update_tracking_summary_with_package_id(package_url: str):
    package = aliased(Package)

    # update package_id in tracking_summary
    subquery = (
        session.query(package.id)
        .filter(
            package.name
            == sa.func.regexp_replace(
                " " + ts.url,
                "^[ ]{1}(/\\w{2}){0,1}" + package_url,
                "",
            )
        )
        .scalar_subquery()
    )

    session.query(ts).filter(
        ts.package_id.is_(None),
        ts.tracking_type == "page",
    ).update(
        {ts.package_id: func.coalesce(subquery, "~~not~found~~")},
        synchronize_session=False,
    )

    ta = aliased(ts)  # tracking_alias

    # Create subquery for total views
    subquery_total = (
        session.query(func.sum(ta.count))
        .filter(
            ta.url == ts.url,
            ta.tracking_date <= ts.tracking_date,
        )
        .scalar_subquery()
    )

    # Create subquery for recent views
    subquery_recent_views = (
        session.query(func.sum(ta.count))
        .filter(
            ta.url == ts.url,
            ta.tracking_date <= ts.tracking_date,
            ta.tracking_date >= ts.tracking_date - 14,
        )
        .scalar_subquery()
    )

    # Update summary totals for 'resource' tracking_type
    session.query(ts).filter(
        ts.running_total == 0,
        ts.tracking_type == "resource",
    ).update(
        {
            ts.running_total: subquery_total,
            ts.recent_views: subquery_recent_views,
        },
        synchronize_session=False,
    )

    # Update summary totals for 'page' tracking_type
    session.query(ts).filter(
        ts.running_total == 0,
        ts.tracking_type == "page",
        ts.package_id.isnot(None),
        ts.package_id != "~~not~found~~",
    ).update(
        {
            ts.running_total: subquery_total,
            ts.recent_views: subquery_recent_views,
        },
        synchronize_session=False,
    )

    session.commit()


def update_tracking_solr(start_date: datetime.datetime):
    results = (
        session.query(ts.package_id)
        .filter(
            ts.package_id != "~~not~found~~",
            ts.tracking_date >= start_date,
        )
        .distinct()
        .all()
    )
    package_ids: set[str] = set()
    for row in results:
        package_ids.add(row[0])

    total = len(package_ids)
    not_found = 0
    click.echo(
        "{} package index{} to be rebuilt starting from {}".format(
            total, "" if total < 2 else "es", start_date
        )
    )

    from ckan.lib.search import rebuild

    for package_id in package_ids:
        try:
            rebuild(package_id)
        except logic.NotFound:
            click.echo("Error: package {} not found.".format(package_id))
            not_found += 1
        except KeyboardInterrupt:
            click.echo("Stopped.")
            return
        except Exception as e:
            error_shout(e)
    click.echo(
        "search index rebuilding done."
        + (" {} not found.".format(not_found) if not_found else "")
    )
