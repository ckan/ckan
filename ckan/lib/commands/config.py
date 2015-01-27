import os
import sys

import paste.script


class ConfigToolCommand(paste.script.command.Command):
    '''Tool for editing options in a CKAN config file

    paster config-tool <default.ini> <key>=<value> [<key>=<value> ...]
    paster config-tool <default.ini> -f <custom_options.ini>

    Examples:
      paster config-tool default.ini sqlalchemy.url=123 'ckan.site_title=ABC'
      paster config-tool default.ini -s server:main -e port=8080
      paster config-tool default.ini -f custom_options.ini
    '''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    default_verbosity = 1
    group_name = 'ckan'
    usage = __doc__
    summary = usage.split('\n')[0]

    parser.add_option('-s', '--section', dest='section',
                      default='app:main', help='Section of the config file')
    parser.add_option(
        '-e', '--edit', action='store_true', dest='edit', default=False,
        help='Checks the option already exists in the config file')
    parser.add_option(
        '-f', '--file', dest='merge_filepath', metavar='FILE',
        help='Supply an options file to merge in')

    def command(self):
        from ckan.lib import config_tool
        if len(self.args) < 1:
            self.parser.error('Not enough arguments (got %i, need at least 1)'
                              % len(self.args))
        config_filepath = self.args[0]
        if not os.path.exists(config_filepath):
            self.parser.error('Config filename %r does not exist.' %
                              config_filepath)
        if self.options.merge_filepath:
            config_tool.config_edit_using_merge_file(
                config_filepath, self.options.merge_filepath)
        options = self.args[1:]
        if not (options or self.options.merge_filepath):
            self.parser.error('No options provided')
        if options:
            for option in options:
                if '=' not in option:
                    sys.stderr.write(
                        'An option does not have an equals sign: %r '
                        'It should be \'key=value\'. If there are spaces '
                        'you\'ll need to quote the option.\n' % option)
                    sys.exit(1)
            try:
                config_tool.config_edit_using_option_strings(
                    config_filepath, options, self.options.section,
                    edit=self.options.edit)
            except config_tool.ConfigToolError, e:
                sys.stderr.write(e.message)
                sys.exit(1)
