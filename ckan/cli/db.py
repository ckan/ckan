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
        print(e)
    print(u'Initialising DB: SUCCESS')


prompt_msg = u'This will delete all of your data!\nDo you want to continue?'


@db.command(u'clean', short_help=u'Clean the database')
@click.confirmation_option(prompt=prompt_msg)
@click.help_option(u'-h', u'--help')
def cleandb():
    u'''Cleaning  the database'''
    try:
        import ckan.model as model
        model.repo.clean_db()
    except Exception as e:
        print(e)
    print(u'Cleaning DB: SUCCESS')


@db.command(u'upgrade', short_help=u'Upgrade the database')
@click.option(u'-v', u'--version', help='Migration version')
@click.help_option(u'-h', u'--help')
def updatedb(version=None):
    u'''Upgrading the database'''
    try:
        import ckan.model as model
        model.repo.upgrade_db(version)
    except Exception as e:
        print(e)
    print(u'Upgrading DB: SUCCESS')


@db.command(u'version', short_help=u'Returns current version of data schema')
@click.help_option(u'-h', u'--help')
def version():
    u'''Return current version'''
    try:
        from ckan.model import Session
        print(Session.execute(u'select version from '
                              u'migrate_version;').fetchall())
    except Exception as e:
        print(e)
