# encoding: utf-8
from __future__ import annotations

import multiprocessing as mp

import click
import sqlalchemy as sa
from ckan.common import config
from . import error_shout


@click.group(name=u'search-index', short_help=u'Search index commands')
@click.help_option(u'-h', u'--help')
def search_index():
    pass


@search_index.command(name=u'rebuild', short_help=u'Rebuild search index')
@click.option(u'-v', u'--verbose', is_flag=True)
@click.option(u'-i', u'--force', is_flag=True,
              help=u'Ignore exceptions when rebuilding the index')
@click.option(u'-o', u'--only-missing',
              help=u'Index non indexed datasets only', is_flag=True)
@click.option(u'-q', u'--quiet', help=u'Do not output index rebuild progress',
              is_flag=True)
@click.option(u'-e', u'--commit-each', is_flag=True,
              help=u'Perform a commit after indexing each dataset. This'
                   u'ensures that changes are immediately available on the'
                   u'search, but slows significantly the process. Default'
                   u'is false.')
@click.option('-c', '--clear', help='Clear the index before reindexing',
              is_flag=True)
@click.argument(u'package_id', required=False)
def rebuild(
        verbose: bool, force: bool, only_missing: bool, quiet: bool,
        commit_each: bool, package_id: str, clear: bool
):
    u''' Rebuild search index '''
    from ckan.lib.search import rebuild, commit
    try:

        rebuild(package_id,
                only_missing=only_missing,
                force=force,
                defer_commit=(not commit_each),
                quiet=quiet and not verbose,
                clear=clear)
    except Exception as e:
        error_shout(e)
    if not commit_each:
        commit()


@search_index.command(name=u'check', short_help=u'Check search index')
def check():
    from ckan.lib.search import check
    check()


@search_index.command(name=u'show', short_help=u'Show index of a dataset')
@click.argument(u'dataset_name')
def show(dataset_name: str):
    from ckan.lib.search import show

    index = show(dataset_name)
    click.echo(index)


@search_index.command(name=u'clear', short_help=u'Clear the search index')
@click.argument(u'dataset_name', required=False)
def clear(dataset_name: str):
    from ckan.lib.search import clear, clear_all

    if dataset_name:
        clear(dataset_name)
    else:
        clear_all()


@search_index.command(name=u'rebuild-fast',
                      short_help=u'Reindex with multiprocessing')
def rebuild_fast():
    from ckan.lib.search import commit

    db_url = config['sqlalchemy.url']
    engine = sa.create_engine(db_url)
    package_ids = []
    result = engine.execute(u"select id from package where state = 'active';")
    for row in result:
        package_ids.append(row[0])

    def start(ids: list[str]):
        from ckan.lib.search import rebuild
        rebuild(package_ids=ids)

    def chunks(list_: list[str], n: int):
        u""" Yield n successive chunks from list_"""
        newn = int(len(list_) / n)
        for i in range(0, n - 1):
            yield list_[i * newn:i * newn + newn]
        yield list_[n * newn - newn:]

    processes = []

    try:
        for chunk in chunks(package_ids, mp.cpu_count()):
            process = mp.Process(target=start, args=(chunk,))
            processes.append(process)
            process.daemon = True
            process.start()

        for process in processes:
            process.join()
        commit()
    except Exception as e:
        error_shout(e)
