# encoding: utf-8

import logging

import click
from ckan.cli import config_tool
from ckan.cli import (
    datapusher,
    click_config_option, db, load_config, search_index, server,
    asset,
    datastore,
    translation,
    dataset,
    plugin_info,
    notify,
    tracking,
    minify,
    less,
    generate
)

from ckan.config.middleware import make_app
from ckan.cli import seed

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


ckan.add_command(config_tool.config_tool)
ckan.add_command(server.run)
ckan.add_command(seed.seed)
ckan.add_command(db.db)
ckan.add_command(datapusher.datapusher)
ckan.add_command(search_index.search_index)
ckan.add_command(asset.asset)
ckan.add_command(datastore.datastore)
ckan.add_command(translation.translation)
ckan.add_command(dataset.dataset)
ckan.add_command(plugin_info.plugin_info)
ckan.add_command(notify.notify)
ckan.add_command(tracking.tracking)
ckan.add_command(minify.minify)
ckan.add_command(less.less)
ckan.add_command(generate.generate)
