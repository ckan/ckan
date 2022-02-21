# encoding: utf-8
from __future__ import annotations

import logging
import click

import ckan.lib.config_tool as ct
from ckan.cli import error_shout

log = logging.getLogger(__name__)


class ConfigOption(click.ParamType):
    name = u'config-option'

    def convert(self, value: str, param: str, ctx: click.Context):
        if u'=' not in value:
            self.fail(
                u'An option does not have an equals sign. '
                u'It should be \'key=value\'. If there are spaces '
                u'you\'ll need to quote the option.\n'
            )
        return value


@click.command(
    name=u'config-tool',
    short_help=u'Tool for editing options in a CKAN config file.'
)
@click.option(
    u'--section',
    u'-s',
    default=u'app:main',
    help=u'Section of the config file'
)
@click.option(
    u'--edit',
    u'-e',
    is_flag=True,
    help=u'Checks the option already exists in the config file.'
)
@click.option(
    u'--file',
    u'-f',
    u'merge_filepath',
    help=u'Supply an options file to merge in.'
)
@click.argument(u'config_filepath', type=click.Path(exists=True))
@click.argument(u'options', nargs=-1, type=ConfigOption())
def config_tool(
        config_filepath: str,
        options: list[str], section: str, edit: bool,
        merge_filepath: str) -> None:
    u'''Tool for editing options in a CKAN config file

    ckan config-tool <default.ini> <key>=<value> [<key>=<value> ...]

    ckan config-tool <default.ini> -f <custom_options.ini>

    Examples:

      ckan config-tool default.ini sqlalchemy.url=123 'ckan.site_title=ABC'

      ckan config-tool default.ini -s server:main -e port=8080

      ckan config-tool default.ini -f custom_options.ini
    '''

    if merge_filepath:
        ct.config_edit_using_merge_file(
            config_filepath, merge_filepath
        )
    if not (options or merge_filepath):
        error_shout(u'No options provided')
        raise click.Abort()
    try:
        ct.config_edit_using_option_strings(
            config_filepath, options, section, edit=edit
        )
    except ct.ConfigToolError as e:
        error_shout(e)
        raise click.Abort()
