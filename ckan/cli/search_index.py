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


def list_orphans(return_list: bool=False) -> list|None:
    import ckan.logic as logic
    search = logic.get_action('package_search')({},{
                'q': '*:*',
                'fl': 'id'})
    indexed_package_ids = {r['id'] for r in search['results']}

    import ckan.model as model
    from sqlalchemy.sql import select
    package_ids = {r[0] for r in select([model.package_table.c['id']]).execute()}

    orphaned_package_ids = []
    for indexed_package_id in indexed_package_ids:
        if indexed_package_id not in package_ids:
            orphaned_package_ids.append(indexed_package_id)

    if return_list:
        return orphaned_package_ids
    from pprint import pprint
    pprint(orphaned_package_ids)


@search_index.command(name=u'list-orphans', short_help=u'Lists any non-existant packages in the search index')
def list_orphans_command():
    return list_orphans()


@search_index.command(name=u'clear-orphans', short_help=u'Clear any non-existant packages in the search index')
@click.option(u'-v', u'--verbose', is_flag=True)
def clear_orphans(verbose: bool=False):
    from ckan.lib.search import clear
    for orphaned_package_id in list_orphans(return_list=True):
        if verbose:
            print("Clearing search index for dataset %s..." % orphaned_package_id)
        clear(orphaned_package_id)


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
