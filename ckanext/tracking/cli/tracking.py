# encoding: utf-8

import datetime
import csv

from typing import NamedTuple, Optional
import re
import click
import sqlalchemy as sa

import ckan.model as model
import ckan.logic as logic
from ckan.cli import error_shout
from ckan.common import config


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
    engine = model.meta.engine
    assert engine
    update_all(engine, start_date)


@tracking.command()
@click.argument('output_file', type=click.Path())
@click.argument('start_date', required=False)
def export(output_file: str, start_date: Optional[str]):
    engine = model.meta.engine
    assert engine

    update_all(engine, start_date)
    export_tracking(engine, output_file)


def update_all(engine: model.Engine, start_date: Optional[str] = None):
    if start_date:
        date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    else:
        # No date given. See when we last have data for and get data
        # from 2 days before then in case new data is available.
        # If no date here then use 2011-01-01 as the start date
        sql = sa.text("""
        SELECT tracking_date from tracking_summary
        ORDER BY tracking_date DESC LIMIT 1;
        """)
        with engine.connect() as conn:
            result = conn.execute(sql).scalar()
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
        update_tracking(engine, date)
        click.echo('tracking updated for {}'.format(date))
        date = stop_date

    update_tracking_solr(engine, start_date_solrsync)


def _total_views(engine: model.Engine):
    sql = sa.text("""
    SELECT p.id, p.name, COALESCE(SUM(s.count), 0) AS total_views
    FROM package AS p
    LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
    GROUP BY p.id, p.name
    ORDER BY total_views DESC
    """)
    with engine.connect() as conn:
        return [ViewCount(*t) for t in conn.execute(sql)]


def _recent_views(engine: model.Engine, measure_from: datetime.date):
    sql = sa.text("""
    SELECT p.id, p.name, COALESCE(SUM(s.count), 0) AS total_views
    FROM package AS p
    LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
    WHERE s.tracking_date >= :from
    GROUP BY p.id, p.name
    ORDER BY total_views DESC
    """)
    with engine.connect() as conn:
        return [
            ViewCount(*t) for t in conn.execute(sql, {"from": measure_from})
        ]


def export_tracking(engine: model.Engine, output_filename: str):
    '''Write tracking summary to a csv file.'''
    headings = [
        'dataset id',
        'dataset name',
        'total views',
        'recent views (last 2 weeks)',
    ]

    measure_from = datetime.date.today() - datetime.timedelta(days=14)
    recent_views = _recent_views(engine, measure_from)
    total_views = _total_views(engine)

    with open(output_filename, 'w') as fh:
        f_out = csv.writer(fh)
        f_out.writerow(headings)
        recent_views_for_id = dict((r.id, r.count) for r in recent_views)
        f_out.writerows([(r.id,
                        r.name,
                        r.count,
                        recent_views_for_id.get(r.id, 0))
                        for r in total_views])


def update_tracking(engine: model.Engine, summary_date: datetime.datetime):
    package_url = '/dataset/'
    root_path = config.get('ckan.root_path')
    root_path = re.sub('/{{LANG}}', '', root_path)
    # clear out existing data before adding new
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
            DELETE FROM tracking_summary
            WHERE tracking_date=:date;
            """),
            {"date": summary_date}
        )

        conn.execute(
            sa.text("""
            SELECT DISTINCT REPLACE(url, :root_path, '') AS tracking_url, user_key,
            CAST(access_timestamp AS Date) AS tracking_date,
            tracking_type INTO tracking_tmp
            FROM tracking_raw
            WHERE CAST(access_timestamp as Date)=:date
            """),
            {"root_path": root_path, "date": summary_date}
        )

        conn.execute(
            sa.text("""
            INSERT INTO tracking_summary
            (url, count, tracking_date, tracking_type)
            SELECT tracking_url, count(user_key), tracking_date, tracking_type
            FROM tracking_tmp
            GROUP BY tracking_url, tracking_date, tracking_type;
            """)
        )
        conn.execute(
            sa.text("""
            DROP TABLE tracking_tmp;
            """)
        )

    with engine.begin() as conn:
        conn.execute(sa.text("""
        UPDATE tracking_summary t
        SET package_id =
        COALESCE(
          (SELECT id FROM package p WHERE p.name =
           regexp_replace (' ' || t.url, '^[ ]{1}(/\\w{2}){0,1}' || :url, '')),
          '~~not~found~~'
        )
        WHERE t.package_id IS NULL
        AND tracking_type = 'page'
        """), {"url": package_url})

        # update summary totals for resources
        conn.execute(sa.text("""
        UPDATE tracking_summary t1
        SET running_total = (
        SELECT sum(count)
        FROM tracking_summary t2
        WHERE t1.url = t2.url
        AND t2.tracking_date <= t1.tracking_date
        )
        ,recent_views = (
        SELECT sum(count)
        FROM tracking_summary t2
        WHERE t1.url = t2.url
        AND t2.tracking_date <= t1.tracking_date
        AND t2.tracking_date >= t1.tracking_date - 14
        )
        WHERE t1.running_total = 0 AND tracking_type = 'resource'
        """))

        # update summary totals for pages
        conn.execute(sa.text("""
        UPDATE tracking_summary t1
        SET running_total = (
        SELECT sum(count)
        FROM tracking_summary t2
        WHERE t1.package_id = t2.package_id
        AND t2.tracking_date <= t1.tracking_date
        )
        ,recent_views = (
        SELECT sum(count)
        FROM tracking_summary t2
        WHERE t1.package_id = t2.package_id
        AND t2.tracking_date <= t1.tracking_date
        AND t2.tracking_date >= t1.tracking_date - 14
        )
        WHERE t1.running_total = 0 AND tracking_type = 'page'
        AND t1.package_id IS NOT NULL
        AND t1.package_id != '~~not~found~~'
        """))


def update_tracking_solr(engine: model.Engine, start_date: datetime.datetime):
    sql = sa.text("""
    SELECT package_id FROM tracking_summary
    where package_id!='~~not~found~~'
    and tracking_date >= :date
    """)
    with engine.connect() as conn:
        results = conn.execute(sql, {"date": start_date})

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
