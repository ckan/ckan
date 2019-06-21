# encoding: utf-8

import os
import logging
import ckan.migration as migration_repo
import click

from ckan.cli import error_shout

log = logging.getLogger(__name__)


@click.group(name=u'db', short_help=u'Database commands')
def db():
    pass


@db.command(u'init', short_help=u'Initialize the database')
def initdb():
    u'''Initialising the database'''
    log.info(u"Initialize the Database")
    try:
        import ckan.model as model
        model.repo.init_db()
    except Exception as e:
        error_shout(e)
    else:
        click.secho(u'Initialising DB: SUCCESS', fg=u'green', bold=True)


PROMPT_MSG = u'This will delete all of your data!\nDo you want to continue?'


@db.command(u'clean', short_help=u'Clean the database')
@click.confirmation_option(prompt=PROMPT_MSG)
def cleandb():
    u'''Cleaning  the database'''
    try:
        import ckan.model as model
        model.repo.clean_db()
    except Exception as e:
        error_shout(e)
    else:
        click.secho(u'Cleaning DB: SUCCESS', fg=u'green', bold=True)


@db.command(u'upgrade', short_help=u'Upgrade the database')
@click.option(u'-v', u'--version', help=u'Migration version', default=u'head')
def updatedb(version):
    u'''Upgrading the database'''
    try:
        import ckan.model as model
        model.repo.upgrade_db(version)
    except Exception as e:
        error_shout(e)
    else:
        click.secho(u'Upgrading DB: SUCCESS', fg=u'green', bold=True)


@db.command(u'downgrade', short_help=u'Downgrade the database')
@click.option(u'-v', u'--version', help=u'Migration version', default=u'base')
def downgradedb(version):
    u'''Downgrading the database'''
    try:
        import ckan.model as model
        model.repo.downgrade_db(version)
    except Exception as e:
        error_shout(e)
    else:
        click.secho(u'Downgrading DB: SUCCESS', fg=u'green', bold=True)


@db.command(u'version', short_help=u'Returns current version of data schema')
@click.option(u'--hash', is_flag=True)
def version(hash):
    u'''Return current version'''
    log.info(u"Returning current DB version")
    import ckan.model as model
    model.repo.setup_migration_version_control()
    current = model.repo.current_version()
    if not hash:
        current = _version_hash_to_ordinal(current)
    click.secho(
        u'Current DB version: {}'.format(current),
        fg=u'green', bold=True
    )


def _version_hash_to_ordinal(version):
    if u'base' == version:
        return 0
    versions_dir = os.path.join(
        os.path.dirname(migration_repo.__file__), u'versions'
    )
    versions = sorted(os.listdir(versions_dir))

    # latest version looks like `123abc (head)`
    if version.endswith(u'(head)'):
        return int(versions[-1].split(u'_')[0])
    for name in versions:
        if version in name:
            return int(name.split(u'_')[0])
    error_shout(u'Version `{}` was not found in {}'.format(
        version, versions_dir
    ))
