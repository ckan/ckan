# encoding: utf-8

from __future__ import print_function

import logging

import click

import ckan.model as model
import ckan.plugins.toolkit as tk
import ckanext.datastore.backend as datastore_backend
from ckan.cli import error_shout

log = logging.getLogger(__name__)

question = (
    "Data in any datastore resource that isn't in their source files "
    "(e.g. data added using the datastore API) will be permanently "
    "lost. Are you sure you want to proceed?"
)
requires_confirmation = click.option(
    '--yes', '-y', is_flag=True, help='Always answer yes to questions'
)


def confirm(yes):
    if yes:
        return
    click.confirm(question, abort=True)


@click.group(short_help="Perform commands in the datapusher.")
def datapusher():
    """Perform commands in the datapusher.
    """
    pass


@datapusher.command()
@requires_confirmation
def resubmit(yes):
    '''Resubmit updated datastore resources.
    '''
    confirm(yes)

    resource_ids = datastore_backend.get_all_resources_ids_in_datastore()
    _submit(resource_ids)


@datapusher.command()
@click.argument('package', required=False)
@requires_confirmation
def submit(package, yes):
    '''Submits resources from package.

    If no package ID/name specified, submits all resources from all
    packages.
    '''
    confirm(yes)

    if not package:
        ids = tk.get_action('package_list')({
            'model': model,
            'ignore_auth': True
        }, {})
    else:
        ids = [package]

    for id in ids:
        package_show = tk.get_action('package_show')
        try:
            pkg = package_show({
                'model': model,
                'ignore_auth': True
            }, {'id': id})
        except Exception as e:
            error_shout(e)
            error_shout("Package '{}' was not found".format(package))
            raise click.Abort()
        if not pkg['resources']:
            continue
        resource_ids = [r['id'] for r in pkg['resources']]
        _submit(resource_ids)


def _submit(resources):
    click.echo('Submitting {} datastore resources'.format(len(resources)))
    user = tk.get_action('get_site_user')({
        'model': model,
        'ignore_auth': True
    }, {})
    datapusher_submit = tk.get_action('datapusher_submit')
    for id in resources:
        click.echo('Submitting {}...'.format(id), nl=False)
        data_dict = {
            'resource_id': id,
            'ignore_hash': True,
        }
        if datapusher_submit({'user': user['name']}, data_dict):
            click.echo('OK')
        else:
            click.echo('Fail')
