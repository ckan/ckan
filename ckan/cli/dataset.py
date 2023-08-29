# encoding: utf-8

import logging
import pprint

import click


import ckan.logic as logic
import ckan.model as model
from ckan.types import Context

log = logging.getLogger(__name__)


@click.group(short_help=u"Manage datasets")
def dataset():
    """Manage datasets.
    """
    pass


@dataset.command()
@click.argument(u'package')
def show(package: str):
    u'''Shows dataset properties.
    '''
    dataset = _get_dataset(package)
    click.echo(pprint.pformat(dataset.as_dict()))


@dataset.command()
def list():
    u'''Lists datasets.
    '''
    click.echo(u'Datasets:')
    datasets = model.Session.query(model.Package)
    click.echo(u'count = %i' % datasets.count())
    for dataset in datasets:
        state = (
            u'(%s)' % dataset.state
        ) if dataset.state != u'active' else u''

        click.echo(
            u'%s %s %s' %
            (click.style(dataset.id, bold=True), dataset.name, state)
        )


@dataset.command()
@click.argument(u'package')
def delete(package: str):
    u'''Changes dataset state to 'deleted'.
    '''
    dataset = _get_dataset(package)
    old_state = dataset.state

    dataset.delete()
    model.repo.commit_and_remove()
    dataset = _get_dataset(package)
    click.echo(
        u'%s %s -> %s' % (
            dataset.name, click.style(old_state, fg=u'red'),
            click.style(dataset.state, fg=u'green')
        )
    )


@dataset.command()
@click.argument(u'package')
def purge(package: str):
    u'''Removes dataset from db entirely.
    '''
    dataset = _get_dataset(package)
    name = dataset.name

    site_user = logic.get_action(u'get_site_user')({u'ignore_auth': True}, {})
    context: Context = {u'user': site_user[u'name'], u'ignore_auth': True}
    logic.get_action(u'dataset_purge')(context, {u'id': package})
    click.echo(u'%s purged' % name)


def _get_dataset(package: str):
    dataset = model.Package.get(str(package))
    assert dataset, u'Could not find dataset matching reference: {}'.format(
        package
    )
    return dataset
