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
@click.help_option(u'-h', u'--help')
@click.confirmation_option(prompt=prompt_msg)
def cleandb():
    u'''Cleaning  the database'''
    try:
        import ckan.model as model
        model.repo.clean_db()
    except Exception as e:
        print(e)
    print(u'Cleaning DB: SUCCESS')


@db.command(u'upgrade', short_help=u'Upgrade the database')
@click.help_option(u'-h', u'--help')
def updatedb():
    u'''Upgrading the database'''
    try:
        import ckan.model as model
        model.repo.upgrade_db()
    except Exception as e:
        print(e)
    print(u'Upgrading DB: SUCCESS')
