# encoding: utf-8

import multiprocessing as mp

import click
import sqlalchemy as sa
import ckan.plugins.toolkit as tk


@click.group(name='search-index', short_help='Search index commands')
@click.help_option('-h', '--help')
def search_index():
    pass


@search_index.command(name='rebuild', short_help='Rebuild search index')
@click.option('-v', '--verbose', is_flag=True)
@click.option('-i', '--force', is_flag=True,
              help='Ignore exceptions when rebuilding the index')
@click.option('-o', '--only-missing',
              help='Index non indexed datasets only', is_flag=True)
@click.option('-q', '--quiet', help='Do not output index rebuild progress',
              is_flag=True)
@click.option('-e', '--commit-each', is_flag=True,
              help='Perform a commit after indexing each dataset. This'
                   'ensures that changes are immediately available on the'
                   'search, but slows significantly the process. Default'
                   'is false.')
@click.option('-c', '--clear', help='Clear the index before reindexing',
              is_flag=True)
@click.argument('package_id', required=False)
def rebuild(
        verbose, force, only_missing, quiet, commit_each, package_id, clear
):
    ''' Rebuild search index '''
    from ckan.lib.search import rebuild, commit
    try:

        rebuild(package_id,
                only_missing=only_missing,
                force=force,
                defer_commit=(not commit_each),
                quiet=quiet,
                clear=clear)
    except Exception as e:
        tk.error_shout(e)
    if not commit_each:
        commit()


@search_index.command(name='check', short_help='Check search index')
def check():
    from ckan.lib.search import check
    check()


@search_index.command(name='show', short_help='Show index of a dataset')
@click.argument('dataset_name')
def show(dataset_name):
    from ckan.lib.search import show

    index = show(dataset_name)
    click.echo(index)


@search_index.command(name='clear', short_help='Clear the search index')
@click.argument('dataset_name', required=False)
def clear(dataset_name):
    from ckan.lib.search import clear, clear_all

    if dataset_name:
        clear(dataset_name)
    else:
        clear_all()


@search_index.command(name='rebuild-fast',
                      short_help='Reindex with multiprocessing')
def rebuild_fast():
    from ckan.lib.search import commit

    db_url = tk.config['sqlalchemy.url']
    engine = sa.create_engine(db_url)
    package_ids = []
    result = engine.execute("select id from package where state = 'active';")
    for row in result:
        package_ids.append(row[0])

    def start(ids):
        from ckan.lib.search import rebuild
        rebuild(package_ids=ids)

    def chunks(list_, n):
        """ Yield n successive chunks from list_"""
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
        click.echo(e.message)
