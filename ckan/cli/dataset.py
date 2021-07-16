# encoding: utf-8

import logging
import pprint

import click
from six import text_type

import ckan.logic as logic
import ckan.model as model

log = logging.getLogger(__name__)


@click.group(short_help="Manage datasets")
def dataset():
    """Manage datasets.
    """
    pass


@dataset.command()
@click.argument('package')
def show(package):
    '''Shows dataset properties.
    '''
    dataset = _get_dataset(package)
    click.echo(pprint.pformat(dataset.as_dict()))


@dataset.command()
def list():
    '''Lists datasets.
    '''
    click.echo('Datasets:')
    datasets = model.Session.query(model.Package)
    click.echo('count = %i' % datasets.count())
    for dataset in datasets:
        state = (
            '(%s)' % dataset.state
        ) if dataset.state != 'active' else ''

        click.echo(
            '%s %s %s' %
            (click.style(dataset.id, bold=True), dataset.name, state)
        )


@dataset.command()
@click.argument('package')
def delete(package):
    '''Changes dataset state to 'deleted'.
    '''
    dataset = _get_dataset(package)
    old_state = dataset.state

    dataset.delete()
    model.repo.commit_and_remove()
    dataset = _get_dataset(package)
    click.echo(
        '%s %s -> %s' % (
            dataset.name, click.style(old_state, fg='red'),
            click.style(dataset.state, fg='green')
        )
    )


@dataset.command()
@click.argument('package')
def purge(package):
    '''Removes dataset from db entirely.
    '''
    dataset = _get_dataset(package)
    name = dataset.name

    site_user = logic.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': site_user['name'], 'ignore_auth': True}
    logic.get_action('dataset_purge')(context, {'id': package})
    click.echo('%s purged' % name)


def _get_dataset(package):
    dataset = model.Package.get(text_type(package))
    assert dataset, 'Could not find dataset matching reference: {}'.format(
        package
    )
    return dataset
