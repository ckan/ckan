# encoding: utf-8

import datetime
import csv

from typing import NamedTuple, Optional

import click
import sqlalchemy as sa
from sqlalchemy import desc, func, select, cast
from sqlalchemy.orm import aliased # https://stackoverflow.com/questions/5350033/usage-of-aliased-in-sqlalchemy-orm

from ckan.model import Package
from ckan.model.meta import Session as session
import ckan.logic as logic
from ckan.cli import error_shout

from ckanext.tracking.model import TrackingSummary, TrackingRaw


class ViewCount(NamedTuple):
    id: str
    name: str
    count: int


@click.group(name='tracking', short_help='Update tracking statistics')
def tracking():
    pass


@tracking.command()
@click.argument('start_date', required=False)
def update(start_date: Optional[str]):
    update_all(start_date)


@tracking.command()
@click.argument('output_file', type=click.Path())
@click.argument('start_date', required=False)
def export(output_file: str, start_date: Optional[str]):
    update_all(start_date)
    export_tracking(output_file)


def update_all(start_date: Optional[str] = None):
    if start_date:
        date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    else:
        # No date given. See when we last have data for and get data
        # from 2 days before then in case new data is available.
        # If no date here then use 2011-01-01 as the start date
        result = session.query(TrackingSummary.tracking_date).order_by(
            desc(TrackingSummary.tracking_date)).first()
        # sql = sa.text("""
        # SELECT tracking_date from tracking_summary
        # ORDER BY tracking_date DESC LIMIT 1;
        # """)
        if result:
            date = result
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
        click.echo('tracking updated for {}'.format(date))
        date = stop_date

    update_tracking_solr(start_date_solrsync)


def _total_views():
    # sql = sa.text("""
    # SELECT p.id, p.name, COALESCE(SUM(s.count), 0) AS total_views
    # FROM package AS p
    # LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
    # GROUP BY p.id, p.name
    # ORDER BY total_views DESC
    # """)
    stmt = select(TrackingSummary.package_id,
                  func.coalesce(
                      func.sum(TrackingSummary.count), 0).label('total_views'))\
        .group_by(TrackingSummary.package_id)\
        .order_by(desc('total_views'))

    return [ViewCount(*t) for t in session.execute(stmt)]


def _recent_views(measure_from: datetime.date):
    # sql = sa.text("""
    # SELECT p.id, p.name, COALESCE(SUM(s.count), 0) AS total_views
    # FROM package AS p
    # LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
    # WHERE s.tracking_date >= :from
    # GROUP BY p.id, p.name
    # ORDER BY total_views DESC
    # """)
    stmt = select(TrackingSummary.package_id, func.coalesce(
                        func.sum(TrackingSummary.count), 0).label('total_views'))\
            .where(TrackingSummary.tracking_date >= measure_from)\
            .group_by(TrackingSummary.package_id)\
            .order_by(desc('total_views'))
    return [ViewCount(*t) for t in session.execute(stmt)]  # {'from': measure_from})


def export_tracking(output_filename: str):
    '''Write tracking summary to a csv file.'''
    headings = [
        'dataset id',
        'dataset name',
        'total views',
        'recent views (last 2 weeks)',
    ]

    measure_from = datetime.date.today() - datetime.timedelta(days=14)
    recent_views = _recent_views(measure_from)
    total_views = _total_views()

    with open(output_filename, 'w') as fh:
        f_out = csv.writer(fh)
        f_out.writerow(headings)
        recent_views_for_id = dict((r.id, r.count) for r in recent_views)
        f_out.writerows([(r.id,
                        r.name,
                        r.count,
                        recent_views_for_id.get(r.id, 0))
                        for r in total_views])


def update_tracking(summary_date: datetime.datetime):
    package_url = '/dataset/'
    # clear out existing data before adding new data
    # with engine.begin() as conn:
    #     conn.execute(
    #         sa.text("""
    #         DELETE FROM tracking_summary
    #         WHERE tracking_date=:date;
    #         """),
    #         {"date": summary_date}
    #     )
    session.query(TrackingSummary).filter(
        TrackingSummary.tracking_date == summary_date).delete()
    # KEEP THIS COMMENTED OUT UNTIL WE ARE SURE THE ABOVE WORKS
    # insert new data into tracking_summary from tracking_raw
    # conn.execute(
    #     sa.text("""
    #     SELECT DISTINCT url, user_key,
    #     CAST(access_timestamp AS Date) AS tracking_date,
    #     tracking_type INTO tracking_tmp
    #     FROM tracking_raw
    #     WHERE CAST(access_timestamp as Date)=:date
    #     """), {"date": summary_date}
    # )
    tracking_tmp = (
        session.query(
            TrackingRaw.url,
            TrackingRaw.user_key,
            cast(TrackingRaw.access_timestamp, sa.Date).label("tracking_date"),  # type: ignore
            TrackingRaw.tracking_type)
        .filter(cast(TrackingRaw.access_timestamp, sa.Date) == summary_date)  # type: ignore
        .distinct().subquery())
    # for url, user_key, tracking_date, tracking_type in tracking_tmp:
    #     summary = TrackingSummary(url=url,
    #                               count=1,
    #                               tracking_date=tracking_date,
    #                               tracking_type=tracking_type)
    #     session.add(summary)
    summary = (session.query(tracking_tmp.c.url,
                             tracking_tmp.c.tracking_date,
                             tracking_tmp.c.tracking_type,
                             func.count(tracking_tmp.c.user_key).label('count'))
               .group_by(tracking_tmp.c.url,
                         tracking_tmp.c.tracking_date,
                         tracking_tmp.c.tracking_type))
    for url, tracking_date, tracking_type, count in summary:
        summary_row = TrackingSummary(url=url,
                                      count=count,
                                      tracking_date=tracking_date,
                                      tracking_type=tracking_type,
                                      package_id=None,
                                      running_total=0,
                                      recent_views=0)
        session.add(summary_row)
    # KEEP THIS COMMENTED OUT UNTIL WE ARE SURE THE ABOVE WORKS
    # conn.execute(
    #     sa.text("""
    #     INSERT INTO tracking_summary
    #     (url, count, tracking_date, tracking_type)
    #     SELECT url, count(user_key), tracking_date, tracking_type
    #     FROM tracking_tmp
    #     GROUP BY url, tracking_date, tracking_type;
    #     """)
    # )
    # conn.execute(
    #     sa.text("""
    #     DROP TABLE tracking_tmp;
    #     """)
    # )
    session.commit()
    update_tracking_summary_with_package_id(package_url)


def update_tracking_summary_with_package_id(package_url: str):
    package = aliased(Package)
    # update package_id in tracking_summary
    subquery = (
        session.query(package.id)
        .filter(package.name == sa.func.regexp_replace(
            ' ' + TrackingSummary.url, '^[ ]{1}(/\\w{2}){0,1}' + package_url, ''))
        .scalar_subquery())

    session.query(TrackingSummary).filter(
        TrackingSummary.package_id.is_(None),  # type: ignore
        TrackingSummary.tracking_type == 'page'
        ).update(
        {
            TrackingSummary.package_id: func.coalesce(subquery, '~~not~found~~')
        },
        synchronize_session=False
        )

    # Update running_total and recent_views for 'resource'
    tracking_alias = aliased(TrackingSummary)

    subquery_total = (
        session.query(func.sum(tracking_alias.count))
        .filter(
            tracking_alias.url == TrackingSummary.url,
            tracking_alias.tracking_date <= TrackingSummary.tracking_date
        )
        .scalar_subquery()
    )

    subquery_recent_views = (
        session.query(func.sum(tracking_alias.count))
        .filter(
            tracking_alias.url == TrackingSummary.url,
            tracking_alias.tracking_date <= TrackingSummary.tracking_date,
            tracking_alias.tracking_date >= TrackingSummary.tracking_date - 14   # type: ignore
        )
        .scalar_subquery()
    )

    session.query(TrackingSummary).filter(
        TrackingSummary.running_total == 0,
        TrackingSummary.tracking_type == 'resource'
    ).update(
        {
            TrackingSummary.running_total: subquery_total,
            TrackingSummary.recent_views: subquery_recent_views
        },
        synchronize_session=False
    )

    # Update summary totals for 'page' tracking_type
    session.query(TrackingSummary).filter(
        TrackingSummary.running_total == 0,
        TrackingSummary.tracking_type == 'page',
        TrackingSummary.package_id.isnot(None),  # type: ignore
        TrackingSummary.package_id != '~~not~found~~'
    ).update(
        {
            TrackingSummary.running_total: subquery_total,
            TrackingSummary.recent_views: subquery_recent_views
        },
        synchronize_session=False
    )

    session.commit()

    # KEEP THIS COMMENTED OUT UNTIL WE ARE SURE THE ABOVE WORKS
    # with engine.begin() as conn:
    #     conn.execute(sa.text("""
    #     UPDATE tracking_summary t
    #     SET package_id =
    #     COALESCE(
    #       (SELECT id FROM package p WHERE p.name =
    #        regexp_replace (' ' || t.url, '^[ ]{1}(/\\w{2}){0,1}' || :url, '')),
    #       '~~not~found~~'
    #     )
    #     WHERE t.package_id IS NULL
    #     AND tracking_type = 'page'
    #     """), {"url": package_url})

    #     # update summary totals for resources
    #     conn.execute(sa.text("""
    #     UPDATE tracking_summary t1
    #     SET running_total = (
    #     SELECT sum(count)
    #     FROM tracking_summary t2
    #     WHERE t1.url = t2.url
    #     AND t2.tracking_date <= t1.tracking_date
    #     )
    #     ,recent_views = (
    #     SELECT sum(count)
    #     FROM tracking_summary t2
    #     WHERE t1.url = t2.url
    #     AND t2.tracking_date <= t1.tracking_date
    #     AND t2.tracking_date >= t1.tracking_date - 14
    #     )
    #     WHERE t1.running_total = 0 AND tracking_type = 'resource'
    #     """))

    #     # update summary totals for pages
    #     conn.execute(sa.text("""
    #     UPDATE tracking_summary t1
    #     SET running_total = (
    #     SELECT sum(count)
    #     FROM tracking_summary t2
    #     WHERE t1.package_id = t2.package_id
    #     AND t2.tracking_date <= t1.tracking_date
    #     )
    #     ,recent_views = (
    #     SELECT sum(count)
    #     FROM tracking_summary t2
    #     WHERE t1.package_id = t2.package_id
    #     AND t2.tracking_date <= t1.tracking_date
    #     AND t2.tracking_date >= t1.tracking_date - 14
    #     )
    #     WHERE t1.running_total = 0 AND tracking_type = 'page'
    #     AND t1.package_id IS NOT NULL
    #     AND t1.package_id != '~~not~found~~'
    #     """))


def update_tracking_solr(start_date: datetime.datetime):

    results = session.query(TrackingSummary.package_id).filter(
        TrackingSummary.package_id != '~~not~found~~',
        TrackingSummary.tracking_date >= start_date
    ).distinct().all()
    # KEEP THIS COMMENTED OUT UNTIL WE ARE SURE THE ABOVE WORKS
    # sql = sa.text("""
    # SELECT package_id FROM tracking_summary
    # where package_id!='~~not~found~~'
    # and tracking_date >= :date
    # """)
    # with engine.connect() as conn:
    #     results = conn.execute(sql, {"date": start_date})

    package_ids: set[str] = set()
    for row in results:
        package_ids.add(row[0])

    total = len(package_ids)
    not_found = 0
    click.echo('{} package index{} to be rebuilt starting from {}'.format(
        total, '' if total < 2 else 'es', start_date)
    )

    from ckan.lib.search import rebuild
    for package_id in package_ids:
        try:
            rebuild(package_id)
        except logic.NotFound:
            click.echo('Error: package {} not found.'.format(package_id))
            not_found += 1
        except KeyboardInterrupt:
            click.echo('Stopped.')
            return
        except Exception as e:
            error_shout(e)
    click.echo(
        'search index rebuilding done.' + (
            ' {} not found.'.format(not_found) if not_found else u''
        )
    )
