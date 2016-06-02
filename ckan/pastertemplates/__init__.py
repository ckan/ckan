# encoding: utf-8

"""A Paste template for creating new CKAN extensions.

Usage::

  paster --plugin=ckan create -t ckanext

See:

* http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/advanced_pylons/creating_paste_templates.html
* http://pythonpaste.org/script/developer.html#templates

"""
import sys

import jinja2
from paste.script.templates import Template, var
from paste.script.create_distro import Command

# Horrible hack to change the behaviour of Paste itself
# Since this module is only imported when commands are
# run, this will not affect any other paster commands.
import re
Command._bad_chars_re = re.compile('[^a-zA-Z0-9_-]')


def jinja2_template_renderer(content_as_string, vars_as_dict, filename=None):
    return jinja2.Environment().from_string(content_as_string).render(
        vars_as_dict)


class CkanextTemplate(Template):
    """A Paste template for a skeleton CKAN extension package.

    """
    _template_dir = 'template/'
    summary = 'CKAN extension project template'
    use_cheetah = True
    template_renderer = staticmethod(jinja2_template_renderer)

    vars = [
        var('description', 'a one-line description of the extension, '
                           'for example: "A simple blog extension for CKAN"'),
        var('author', 'for example: "Guybrush Threepwood"'),
        var('author_email', 'for example: "guybrush@meleeisland.com"'),
        var('keywords', 'a space-separated list of keywords, for example: '
                        '"CKAN blog"'),
        var('github_user_name', 'your GitHub user or organization name, for '
                                'example: "guybrush" or "ckan"'),
    ]

    def check_vars(self, vars, cmd):
        vars = Template.check_vars(self, vars, cmd)

        # workaround for a paster issue https://github.com/ckan/ckan/issues/2636
        # this is only used from a short-lived paster command
        reload(sys)
        sys.setdefaultencoding('utf-8')

        if not vars['project'].startswith('ckanext-'):
            print "\nError: Project name must start with 'ckanext-'"
            sys.exit(1)

        # The project name without the ckanext-.
        vars['project_shortname'] = vars['project'][len('ckanext-'):]

        # Make sure keywords contains "CKAN" (upper-case) once only.
        keywords = vars['keywords'].strip().split()
        keywords = [keyword for keyword in keywords
                    if keyword not in ('ckan', 'CKAN')]
        keywords.insert(0, 'CKAN')
        vars['keywords'] = u' '.join(keywords)

        # For an extension named ckanext-example we want a plugin class
        # named ExamplePlugin.
        vars['plugin_class_name'] = vars['project_shortname'].title() + 'Plugin'

        return vars
