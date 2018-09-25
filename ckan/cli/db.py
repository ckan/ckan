# encoding: utf-8

import os

import click
from flask import Flask, current_app
from werkzeug.serving import run_simple

from ckan.cli import click_config_option


@click.group(name=u'db', short_help=u'Database commands')
@click.help_option(u'-h', u'--help')
def db():
    pass


@db.command(u'init', short_help=u'Initialaze the database')
@click.help_option(u'-h', u'--help')
def initdb():
    u'''Initialising the database'''
    try:
        import ckan.model as model
        model.repo.init_db()
    except Exception as e:
        click.echo(e, err=True)
    print(u'Initialising DB: SUCCESS')


PROMPT_MSG = u'This will delete all of your data!\nDo you want to continue?'


@db.command(u'clean', short_help=u'Clean the database')
@click.confirmation_option(prompt=PROMPT_MSG)
@click.help_option(u'-h', u'--help')
def cleandb():
    u'''Cleaning  the database'''
    try:
        import ckan.model as model
        model.repo.clean_db()
    except Exception as e:
        click.echo(e, err=True)
    click.secho(u'Cleaning DB: SUCCESS', color=u"green", bold=True)


@db.command(u'upgrade', short_help=u'Upgrade the database')
@click.option(u'-v', u'--version', help=u'Migration version')
@click.help_option(u'-h', u'--help')
def updatedb(version=None):
    u'''Upgrading the database'''
    try:
        import ckan.model as model
        model.repo.upgrade_db(version)
    except Exception as e:
        click.echo(e, err=True)
    click.secho(u'Upgrading DB: SUCCESS', fg=u'green', bold=True)


@db.command(u'version', short_help=u'Returns current version of data schema')
@click.help_option(u'-h', u'--help')
def version():
    u'''Return current version'''
    try:
        from ckan.model import Session
        ver = Session.execute(u'select version from '
                              u'migrate_version;').fetchall()
        click.secho(u"Latest data schema version: {0}".format(ver[0][0]),
                    fg=u"green", bold=True)
    except Exception as e:
        click.echo(e, err=True)
