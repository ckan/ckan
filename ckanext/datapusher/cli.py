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
    u"Data in any datastore resource that isn't in their source files "
    u"(e.g. data added using the datastore API) will be permanently "
    u"lost. Are you sure you want to proceed?"
)
requires_confirmation = click.option(
    u'--yes', u'-y', is_flag=True, help=u'Always answer yes to questions'
)


def confirm(yes):
    if yes:
        return
    click.confirm(question, abort=True)


@click.group()
def datapusher():
    u'''Perform commands in the datapusher.
    '''


@datapusher.command()
@requires_confirmation
def resubmit(yes):
    u'''Resubmit updated datastore resources.
    '''
    confirm(yes)

    resource_ids = datastore_backend.get_all_resources_ids_in_datastore()
    _submit(resource_ids)


@datapusher.command()
@click.argument(u'package', required=False)
@requires_confirmation
def submit(package, yes):
    u'''Submits resources from package.

    If no package ID/name specified, submits all resources from all
    packages.
    '''
    confirm(yes)

    if not package:
        ids = tk.get_action(u'package_list')({
            u'model': model,
            u'ignore_auth': True
        }, {})
    else:
        ids = [package]

    for id in ids:
        package_show = tk.get_action(u'package_show')
        try:
            pkg = package_show({
                u'model': model,
                u'ignore_auth': True
            }, {u'id': id})
        except Exception as e:
            error_shout(e)
            error_shout(u"Package '{}' was not found".format(package))
            raise click.Abort()
        if not pkg[u'resources']:
            continue
        resource_ids = [r[u'id'] for r in pkg[u'resources']]
        _submit(resource_ids)


def _submit(resources):
    click.echo(u'Submitting {} datastore resources'.format(len(resources)))
    user = tk.get_action(u'get_site_user')({
        u'model': model,
        u'ignore_auth': True
    }, {})
    datapusher_submit = tk.get_action(u'datapusher_submit')
    for id in resources:
        click.echo(u'Submitting {}...'.format(id), nl=False)
        data_dict = {
            u'resource_id': id,
            u'ignore_hash': True,
        }
        if datapusher_submit({u'user': user[u'name']}, data_dict):
            click.echo(u'OK')
        else:
            click.echo(u'Fail')
