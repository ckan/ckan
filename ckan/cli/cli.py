# encoding: utf-8
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional
from pkg_resources import iter_entry_points  # type: ignore

import click
import sys

import ckan.plugins as p
import ckan.cli as ckan_cli
from ckan.config.middleware import make_app
from ckan.exceptions import CkanConfigurationException
from . import (
    asset,
    config,
    clean,
    dataset,
    db, search_index, server,
    generate,
    jobs,
    notify,
    plugin_info,
    profile,
    sass,
    sysadmin,
    tracking,
    translation,
    user,
    views,
    config_tool,
    error_shout,
    shell
)

META_ATTR = u'_ckan_meta'
CMD_TYPE_PLUGIN = u'plugin'
CMD_TYPE_ENTRY = u'entry_point'

log = logging.getLogger(__name__)

_no_config_commands = [
    [u'config-tool'],
    [u'generate', u'config'],
    [u'generate', u'extension'],
]


class CtxObject(object):

    def __init__(self, conf: Optional[str] = None):
        # Don't import `load_config` by itself, rather call it using
        # module so that it can be patched during tests
        raw_config = ckan_cli.load_config(conf)
        self.app = make_app(raw_config)

        # Attach the actual CKAN config object to the context
        from ckan.common import config
        self.config = config


class ExtendableGroup(click.Group):
    _section_titles = {
        CMD_TYPE_PLUGIN: u'Plugins',
        CMD_TYPE_ENTRY: u'Entry points',
    }

    def format_commands(
            self, ctx: click.Context, formatter: click.HelpFormatter):
        """Print help message.

        Includes information about commands that were registered by extensions.
        """
        # click won't parse config file from envvar if no other options
        # provided, except for `--help`. In this case it has to be done
        # manually.
        if not ctx.obj:
            _add_ctx_object(ctx)
            _add_external_commands(ctx)

        commands = []
        ext_commands = defaultdict(lambda: defaultdict(list))

        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            help = cmd.short_help or u''

            meta = getattr(cmd, META_ATTR, None)
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
                for rows in group.values():
                    formatter.write_dl(rows)

    def parse_args(self, ctx: click.Context, args: list[str]):
        """Preprocess options and arguments.

        As long as at least one option is provided, click won't fallback to
        printing help message. That means that `ckan -c config.ini` will be
        executed as command, instead of just printing help message(as `ckan -c
        config.ini --help`).
        In order to fix it, we have to check whether there is at least one
        argument. If no, let's print help message manually

        """
        result = super().parse_args(ctx, args)
        if not ctx.protected_args and not ctx.args:
            click.echo(ctx.get_help(), color=ctx.color)
            ctx.exit()
        return result


def _init_ckan_config(ctx: click.Context, param: str, value: str):
    if any(sys.argv[1:len(cmd) + 1] == cmd for cmd in _no_config_commands):
        return
    _add_ctx_object(ctx, value)
    _add_external_commands(ctx)


def _add_ctx_object(ctx: click.Context, path: Optional[str] = None):
    """Initialize CKAN App using config file available under provided path.

    """
    try:
        ctx.obj = CtxObject(path)
    except CkanConfigurationException as e:
        error_shout(e)
        ctx.abort()

    ctx.meta["flask_app"] = ctx.obj.app._wsgi_app

    # Remove all commands that were registered by extensions before
    # adding new ones. Such situation is possible only during tests,
    # because we are using singleton as main entry point, so it
    # preserves its state even between tests
    commands = getattr(ctx.command, "commands")
    for key, cmd in list(commands.items()):
        if hasattr(cmd, META_ATTR):
            commands.pop(key)


def _add_external_commands(ctx: click.Context):
    add = getattr(ctx.command, "add_command")
    for cmd in _get_commands_from_entry_point():
        add(cmd)

    plugins = p.PluginImplementations(p.IClick)
    for cmd in _get_commands_from_plugins(plugins):
        add(cmd)


def _command_with_ckan_meta(cmd: click.Command, name: str, type_: str):
    """Mark command as one retrived from CKAN extension.

    This information is used when CLI help text is generated.
    """
    setattr(cmd, META_ATTR, {u'name': name, u'type': type_})
    return cmd


def _get_commands_from_plugins(plugins: p.PluginImplementations[p.IClick]):
    """Register commands that are available when plugin enabled.

    """
    for plugin in plugins:
        for cmd in plugin.get_commands():
            yield _command_with_ckan_meta(cmd, plugin.name, CMD_TYPE_PLUGIN)


def _get_commands_from_entry_point(entry_point: str = 'ckan.click_command'):
    """Register commands that are available even if plugin is not enabled.

    """
    registered_entries = {}
    for entry in iter_entry_points(entry_point):
        if entry.name in registered_entries:
            error_shout((
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

        yield _command_with_ckan_meta(entry.load(), entry.name, CMD_TYPE_ENTRY)


@click.group(cls=ExtendableGroup)
@click.option(
    u'-c', u'--config', metavar=u'CONFIG',
    is_eager=True, callback=_init_ckan_config, expose_value=False,
    help=u'Config file to use (default: ckan.ini)')
@click.help_option(u'-h', u'--help')
def ckan():
    pass


ckan.add_command(asset.asset)
ckan.add_command(config.config)
ckan.add_command(config_tool.config_tool)
ckan.add_command(dataset.dataset)
ckan.add_command(db.db)
ckan.add_command(generate.generate)
ckan.add_command(jobs.jobs)
ckan.add_command(notify.notify)
ckan.add_command(plugin_info.plugin_info)
ckan.add_command(profile.profile)
ckan.add_command(sass.sass)
ckan.add_command(search_index.search_index)
ckan.add_command(server.run)
ckan.add_command(sysadmin.sysadmin)
ckan.add_command(tracking.tracking)
ckan.add_command(translation.translation)
ckan.add_command(user.user)
ckan.add_command(views.views)
ckan.add_command(shell.shell)
ckan.add_command(clean.clean)
