# encoding: utf-8

import os
import click
from flask import Flask, current_app
from flask.cli import FlaskGroup, with_appcontext

from ckan.common import config
from ckan.lib.cli import (click_config_option, load_config, parse_db_config,
                          paster_click_group)

import pdb; pdb.set_trace()
os.environ['FLASK_RUN_FROM_CLI'] = 'true'

@click.help_option(u'-h', u'--help')
@click_config_option
def run():
    #load_config(config or ctx.obj['config'])
    click.echo('Starting CKAN')
