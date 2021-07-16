# encoding: utf-8

import logging

import click

from ckan.cli import error_shout
import ckan.lib.config_tool as ct

log = logging.getLogger(__name__)


class ConfigOption(click.ParamType):
    name = 'config-option'

    def convert(self, value, param, ctx):
        if '=' not in value:
            self.fail(
                'An option does not have an equals sign. '
                'It should be \'key=value\'. If there are spaces '
                'you\'ll need to quote the option.\n'
            )
        return value


@click.command(
    name='config-tool',
    short_help='Tool for editing options in a CKAN config file.'
)
@click.option(
    '--section',
    '-s',
    default='app:main',
    help='Section of the config file'
)
@click.option(
    '--edit',
    '-e',
    is_flag=True,
    help='Checks the option already exists in the config file.'
)
@click.option(
    '--file',
    '-f',
    'merge_filepath',
    help='Supply an options file to merge in.'
)
@click.argument('config_filepath', type=click.Path(exists=True))
@click.argument('options', nargs=-1, type=ConfigOption())
def config_tool(config_filepath, options, section, edit, merge_filepath):
    '''Tool for editing options in a CKAN config file

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
        error_shout('No options provided')
        raise click.Abort()
    try:
        ct.config_edit_using_option_strings(
            config_filepath, options, section, edit=edit
        )
    except ct.ConfigToolError as e:
        error_shout(e)
        raise click.Abort()
