# encoding: utf-8

import logging

import click
from webassets import script
from webassets.exceptions import BundleError

from ckan.lib import webassets_tools
from ckan.cli import error_shout

log = logging.getLogger(__name__)


@click.group()
def asset():
    """WebAssets commands.

    """
    pass


@asset.command()
def build():
    """Builds all bundles.

    Builds bundles, regardless of whether they are changed or not.
    """
    script.main(['build'], webassets_tools.env)
    click.secho(u'Compile assets: SUCCESS', fg=u'green', bold=True)


@asset.command()
def watch():
    """Watch changes in source files.

    Start a daemon which monitors source files, and rebuilds bundles.

    This can be useful during development, if building is not
    instantaneous, and you are losing valuable time waiting for the
    build to finish while trying to access your site.

    """
    script.main(['watch'], webassets_tools.env)


@asset.command()
def clean():
    """Clear cache.

    Will clear out the cache, which after a while can grow quite large.

    """
    try:
        script.main(['clean'], webassets_tools.env)
    except BundleError as e:
        return error_shout(e)
    click.secho(u'Clear cache: SUCCESS', fg=u'green', bold=True)
