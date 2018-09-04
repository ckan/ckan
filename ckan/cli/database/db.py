# encoding: utf-8

import os

import click
from flask import Flask, current_app

from werkzeug.serving import run_simple

from ckan.cli import click_config_option, load_config
from ckan.config.environment import load_environment
from ckan.config.middleware import make_app


@click.group(name=u'db', short_help=u'Database commands')
@click.help_option(u'-h', u'--help')
def db():
    pass


@db.command(u'init', short_help=u'Initialaze the database')
@click.help_option(u'-h', u'--help')
@click_config_option
def initdb(config):
    u'''Initialising the database'''
    conf = load_config(config)
    load_environment(conf.global_conf, conf.local_conf)
    try:
        import ckan.model as model
        model.repo.init_db()
    except Exception as e:
        print(e)
    print(u'Initialising DB: SUCCESS')


@db.command(u'clean', short_help=u'Clean the database')
@click.help_option(u'-h', u'--help')
@click_config_option
@click.confirmation_option(prompt=u'This will delete all the data! Do you want to continue?')
def cleandb(config):
    u'''Cleaning  the database'''
    conf = load_config(config)
    load_environment(conf.global_conf, conf.local_conf)
    try:
        import ckan.model as model
        model.repo.clean_db()
    except Exception as e:
        print(e)
    print(u'Cleaning DB: SUCCESS')


@db.command(u'upgrade', short_help=u'Upgrade the database')
@click.help_option(u'-h', u'--help')
@click_config_option
def updatedb(config):
    u'''Upgrading the database'''
    conf = load_config(config)
    load_environment(conf.global_conf, conf.local_conf)
    try:
        import ckan.model as model
        model.repo.upgrade_db()
    except Exception as e:
        print(e)
    print(u'Upgrading DB: SUCCESS')
