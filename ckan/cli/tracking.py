# encoding: utf-8

import ckan.model as model
import click
import datetime
import csv
import ckan.logic as logic
from collections import namedtuple
from ckan.cli import error_shout

_ViewCount = namedtuple('ViewCount', 'id name count')


@click.group(name='tracking', short_help='Update tracking statistics')
def tracking():
    pass


@tracking.command()
@click.argument('start_date', required=False)
def update(start_date):
    engine = model.meta.engine
    update_all(engine, start_date)


@tracking.command()
@click.argument('output_file', type=click.Path())
@click.argument('start_date', required=False)
def export(output_file, start_date):
    engine = model.meta.engine

    update_all(engine, start_date)
    export_tracking(engine, output_file)


def update_all(engine, start_date=None):
    if start_date:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    else:
        # No date given. See when we last have data for and get data
        # from 2 days before then in case new data is available.
        # If no date here then use 2011-01-01 as the start date
        sql = '''SELECT tracking_date from tracking_summary
                    ORDER BY tracking_date DESC LIMIT 1;'''
        result = engine.execute(sql).fetchall()
        if result:
            start_date = result[0]['tracking_date']
            start_date += datetime.timedelta(-2)
            # convert date to datetime
            combine = datetime.datetime.combine
            start_date = combine(start_date, datetime.time(0))
        else:
            start_date = datetime.datetime(2011, 1, 1)
    start_date_solrsync = start_date
    end_date = datetime.datetime.now()

    while start_date < end_date:
        stop_date = start_date + datetime.timedelta(1)
        update_tracking(engine, start_date)
        click.echo('tracking updated for {}'.format(start_date))
        start_date = stop_date

    update_tracking_solr(engine, start_date_solrsync)


def _total_views(engine):
    sql = '''
        SELECT p.id,
                p.name,
                COALESCE(SUM(s.count), 0) AS total_views
            FROM package AS p
            LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
            GROUP BY p.id, p.name
            ORDER BY total_views DESC
    '''
    return [_ViewCount(*t) for t in engine.execute(sql).fetchall()]


def _recent_views(engine, measure_from):
    sql = '''
        SELECT p.id,
                p.name,
                COALESCE(SUM(s.count), 0) AS total_views
            FROM package AS p
            LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
            WHERE s.tracking_date >= %(measure_from)s
            GROUP BY p.id, p.name
            ORDER BY total_views DESC
    '''
    return [
        _ViewCount(*t) for t in engine.execute(
            sql, measure_from=str(measure_from)
        ).fetchall()
    ]


def export_tracking(engine, output_filename):
    '''Write tracking summary to a csv file.'''
    HEADINGS = [
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
        f_out.writerow(HEADINGS)
        recent_views_for_id = dict((r.id, r.count) for r in recent_views)
        f_out.writerows([(r.id,
                        r.name,
                        r.count,
                        recent_views_for_id.get(r.id, 0))
                        for r in total_views])


def update_tracking(engine, summary_date):
    PACKAGE_URL = '/dataset/'
    # clear out existing data before adding new
    sql = '''DELETE FROM tracking_summary
                WHERE tracking_date='%s'; ''' % summary_date
    engine.execute(sql)

    sql = '''SELECT DISTINCT url, user_key,
                    CAST(access_timestamp AS Date) AS tracking_date,
                    tracking_type INTO tracking_tmp
                FROM tracking_raw
                WHERE CAST(access_timestamp as Date)=%s;

                INSERT INTO tracking_summary
                (url, count, tracking_date, tracking_type)
                SELECT url, count(user_key), tracking_date, tracking_type
                FROM tracking_tmp
                GROUP BY url, tracking_date, tracking_type;

                DROP TABLE tracking_tmp;
                COMMIT;'''
    engine.execute(sql, summary_date)

    # get ids for dataset urls
    sql = '''UPDATE tracking_summary t
                SET package_id = COALESCE(
                    (SELECT id FROM package p
                    WHERE p.name = regexp_replace
                      (' ' || t.url, '^[ ]{1}(/\\w{2}){0,1}' || %s, ''))
                    ,'~~not~found~~')
                WHERE t.package_id IS NULL
                AND tracking_type = 'page';'''
    engine.execute(sql, PACKAGE_URL)

    # update summary totals for resources
    sql = '''UPDATE tracking_summary t1
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
                WHERE t1.running_total = 0 AND tracking_type = 'resource';'''
    engine.execute(sql)

    # update summary totals for pages
    sql = '''UPDATE tracking_summary t1
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
                AND t1.package_id != '~~not~found~~';'''
    engine.execute(sql)


def update_tracking_solr(engine, start_date):
    sql = '''SELECT package_id FROM tracking_summary
            where package_id!='~~not~found~~'
            and tracking_date >= %s;'''
    results = engine.execute(sql, start_date)

    package_ids = set()
    for row in results:
        package_ids.add(row['package_id'])

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
            ' {} not found.'.format(not_found) if not_found else ''
        )
    )
