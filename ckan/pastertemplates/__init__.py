"""
Paste template for new ckanext.plugins projects
"""

from paste.script.templates import Template, var
from paste.util.template import paste_script_template_renderer
from paste.script.create_distro import Command
import sys

# Horrible hack to change the behaviour of Paste itself
# Since this module is only imported when commands are
# run, this will not affect any other paster commands.
import re
Command._bad_chars_re = re.compile('[^a-zA-Z0-9_-]')

class CkanextTemplate(Template):

    """
    Template to build a skeleton ckanext.plugins package
    """

    _template_dir = 'template/'
    summary = 'CKAN extension project template'
    template_renderer = staticmethod(paste_script_template_renderer)

    vars = [
        var('version', 'Version (like 0.1)'),
        var('description', 'One-line description of the package'),
        var('author', 'Author name'),
        var('author_email', 'Author email'),
        var('url', 'URL of homepage'),
        var('license_name', 'License name'),
    ]

    def check_vars(self, vars, cmd):
        vars = Template.check_vars(self, vars, cmd)
        if not vars['project'].startswith('ckanext-'):
            print "\nError: Expected the project name to start with 'ckanext-'"
            sys.exit(1)
        vars['project'] = vars['project'][len('ckanext-'):]
        return vars
