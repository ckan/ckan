# encoding: utf-8

import logging

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
@click.option(u'-v', u'--version', help=u'Migration version')
def updatedb(version=None):
    u'''Upgrading the database'''
    try:
        import ckan.model as model
        model.repo.upgrade_db(version)
    except Exception as e:
        error_shout(e)
    else:
        click.secho(u'Upgrading DB: SUCCESS', fg=u'green', bold=True)


@db.command(u'version', short_help=u'Returns current version of data schema')
def version():
    u'''Return current version'''
    log.info(u"Returning current DB version")
    try:
        from ckan.model import Session
        ver = Session.execute(u'select version from '
                              u'migrate_version;').fetchall()
        click.secho(
            u"Latest data schema version: {0}".format(ver[0][0]),
            bold=True
        )
    except Exception as e:
        error_shout(e)
