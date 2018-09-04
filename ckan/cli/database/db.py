# encoding: utf-8

import os

import click
from flask import Flask, current_app
from werkzeug.serving import run_simple

from ckan.config.middleware import make_app
from ckan.cli import load_config, click_config_option


@click.command(u'db', short_help=u'Initialize the database')
@click.help_option(u'-h', u'--help')
@click_config_option
@click.argument(u'init')
def initdb(config, init):
    u'''Initialising the database'''
    conf = _load_config(config)
    load_environment(conf.global_conf, conf.local_conf)
    try:
        import ckan.model as model
        model.repo.init_db()
    except Exception as e:
        print(e)
    print(u'Initialising DB: SUCCESS')
