# encoding: utf-8

import logging

import click

from ckan.cli import click_config_option, db, load_config, search_index, server
from ckan.config.middleware import make_app

log = logging.getLogger(__name__)


class CkanCommand(object):

    def __init__(self, conf=None):
        self.config = load_config(conf)
        self.app = make_app(self.config.global_conf, **self.config.local_conf)


@click.group()
@click.help_option(u'-h', u'--help')
@click_config_option
@click.pass_context
def ckan(ctx, config, *args, **kwargs):
    ctx.obj = CkanCommand(config)


ckan.add_command(server.run)
ckan.add_command(db.db)
ckan.add_command(search_index.search_index)
