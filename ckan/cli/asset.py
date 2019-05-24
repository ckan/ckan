# encoding: utf-8

import logging

import click
from webassets import script
from webassets.exceptions import BundleError

from ckan.lib import webassets_tools
from ckan.cli import error_shout

log = logging.getLogger(__name__)


@click.group(name=u'asset', short_help=u'WebAssets commands')
def asset():
    pass


@asset.command(u'build', short_help=u'Builds all bundles.')
def build():
    u'''Builds bundles, regardless of whether they are changed or not.'''
    script.main(['build'], webassets_tools.env)
    click.secho(u'Compile assets: SUCCESS', fg=u'green', bold=True)


@asset.command(u'watch', short_help=u'Watch changes in source files.')
def watch():
    u'''Start a daemon which monitors source files, and rebuilds bundles.

    This can be useful during development, if building is not
    instantaneous, and you are losing valuable time waiting for the
    build to finish while trying to access your site.

    '''
    script.main(['watch'], webassets_tools.env)


@asset.command(u'clean', short_help=u'Clear cache.')
def clean():
    u'''Will clear out the cache, which after a while can grow quite large.'''
    try:
        script.main(['clean'], webassets_tools.env)
    except BundleError as e:
        return error_shout(e)
    click.secho(u'Clear cache: SUCCESS', fg=u'green', bold=True)
