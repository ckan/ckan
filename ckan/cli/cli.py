# encoding: utf-8

import logging
from collections import defaultdict
from pkg_resources import iter_entry_points

import six
import click
import sys

import ckan.plugins as p
import ckan.cli as ckan_cli
from ckan.config.middleware import make_app
from ckan.exceptions import CkanConfigurationException
from ckan.cli import (
    config_tool,
    jobs,
    front_end_build,
    db, search_index, server,
    profile,
    asset,
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

_no_config_commands = [
    [u'config-tool'],
    [u'generate', u'config'],
    [u'generate', u'extension'],
]


class CkanCommand(object):

    def __init__(self, conf=None):
        # Don't import `load_config` by itself, rather call it using
        # module so that it can be patched during tests
        self.config = ckan_cli.load_config(conf)
        self.app = make_app(self.config)


def _get_commands_from_plugins(plugins):
    for plugin in plugins:
        for cmd in plugin.get_commands():
            cmd._ckan_meta = {
                u'name': plugin.name,
                u'type': u'plugin'
            }
            yield cmd


def _get_commands_from_entry_point(entry_point=u'ckan.click_command'):
    registered_entries = {}
    for entry in iter_entry_points(entry_point):
        if entry.name in registered_entries:
            p.toolkit.error_shout((
                u'Attempt to override entry_point `{name}`.\n'
                u'First encounter:\n\t{first!r}\n'
                u'Second encounter:\n\t{second!r}\n'
                u'Either uninstall one of mentioned extensions or update'
                u' corresponding `setup.py` and re-install the extension.'
            ).format(
                name=entry.name,
                first=registered_entries[entry.name].dist,
                second=entry.dist))
            raise click.Abort()
        registered_entries[entry.name] = entry

        cmd = entry.load()
        cmd._ckan_meta = {
            u'name': entry.name,
            u'type': u'entry_point'
        }
        yield cmd


def _init_ckan_config(ctx, param, value):
    is_help = u'--help' in sys.argv
    no_config = False
    if len(sys.argv) > 1:
        for cmd in _no_config_commands:
            if sys.argv[1:len(cmd) + 1] == cmd:
                no_config = True
                break
    if no_config or is_help:
        return

    try:
        ctx.obj = CkanCommand(value)
    except CkanConfigurationException as e:
        p.toolkit.error_shout(e)
        raise click.Abort()

    if six.PY2:
        ctx.meta["flask_app"] = ctx.obj.app.apps["flask_app"]._wsgi_app
    else:
        ctx.meta["flask_app"] = ctx.obj.app._wsgi_app

    for cmd in _get_commands_from_entry_point():
        ctx.command.add_command(cmd)

    plugins = p.PluginImplementations(p.IClick)
    for cmd in _get_commands_from_plugins(plugins):
        ctx.command.add_command(cmd)


click_config_option = click.option(
    u'-c',
    u'--config',
    default=None,
    metavar=u'CONFIG',
    help=u'Config file to use (default: development.ini)',
    is_eager=True,
    callback=_init_ckan_config
)


class CustomGroup(click.Group):
    _section_titles = {
        u'plugin': u'Plugins',
        u'entry_point': u'Entry points',
    }

    def format_commands(self, ctx, formatter):
        # Without any arguments click skips option callbacks.
        self.parse_args(ctx, [u'help'])

        commands = []
        ext_commands = defaultdict(lambda: defaultdict(list))

        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            help = cmd.short_help or u''

            meta = getattr(cmd, u'_ckan_meta', None)
            if meta:
                ext_commands[meta[u'type']][meta[u'name']].append(
                    (subcommand, help))
            else:
                commands.append((subcommand, help))

        if commands:
            with formatter.section(u'Commands'):
                formatter.write_dl(commands)

        for section, group in ext_commands.items():
            with formatter.section(self._section_titles.get(section, section)):
                for _ext, rows in group.items():
                    formatter.write_dl(rows)


@click.group(cls=CustomGroup)
@click.help_option(u'-h', u'--help')
@click_config_option
def ckan(config, *args, **kwargs):
    pass


ckan.add_command(jobs.jobs)
ckan.add_command(config_tool.config_tool)
ckan.add_command(front_end_build.front_end_build)
ckan.add_command(server.run)
ckan.add_command(profile.profile)
ckan.add_command(seed.seed)
ckan.add_command(db.db)
ckan.add_command(search_index.search_index)
ckan.add_command(sysadmin.sysadmin)
ckan.add_command(asset.asset)
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
