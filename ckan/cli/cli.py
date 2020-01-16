# encoding: utf-8

import logging
from collections import defaultdict

import click
from ckan.cli import config_tool
from ckan.cli import (
    jobs,
    datapusher,
    front_end_build,
    click_config_option, db, search_index, server,
    profile,
    asset,
    datastore,
    sysadmin,
    translation,
    dataset,
    views,
    plugin_info,
    notify,
    tracking,
    minify,
    less,
    generate,
    user
)

from ckan.cli import seed

log = logging.getLogger(__name__)


class CustomGroup(click.Group):
    def get_command(self, ctx, name):
        cmd = super(CustomGroup, self).get_command(ctx, name)
        if not cmd:
            ctx.forward(self)
            cmd = super(CustomGroup, self).get_command(ctx, name)
        return cmd

    def format_commands(self, ctx, formatter):
        super(CustomGroup, self).format_commands(ctx, formatter)
        ctx.invoke(self)

        ext_commands = defaultdict(list)
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or not hasattr(cmd, u'_ckanext'):
                continue

            help = cmd.short_help or u''
            ext_commands[cmd._ckanext].append((subcommand, help))
        if ext_commands:
            with formatter.section(u'Plugins'):
                for ext, rows in ext_commands.items():
                    with formatter.section(ext):
                        formatter.write_dl(rows)


@click.group(cls=CustomGroup)
@click.help_option(u'-h', u'--help')
@click_config_option
# @click.pass_context
def ckan(config, *args, **kwargs):
    pass


ckan.add_command(jobs.jobs)
ckan.add_command(config_tool.config_tool)
ckan.add_command(front_end_build.front_end_build)
ckan.add_command(server.run)
ckan.add_command(profile.profile)
ckan.add_command(seed.seed)
ckan.add_command(db.db)
ckan.add_command(datapusher.datapusher)
ckan.add_command(search_index.search_index)
ckan.add_command(sysadmin.sysadmin)
ckan.add_command(asset.asset)
ckan.add_command(datastore.datastore)
ckan.add_command(translation.translation)
ckan.add_command(dataset.dataset)
ckan.add_command(views.views)
ckan.add_command(plugin_info.plugin_info)
ckan.add_command(notify.notify)
ckan.add_command(tracking.tracking)
ckan.add_command(minify.minify)
ckan.add_command(less.less)
ckan.add_command(generate.generate)
ckan.add_command(user.user)
