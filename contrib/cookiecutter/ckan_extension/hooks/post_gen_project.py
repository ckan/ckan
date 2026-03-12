# encoding: utf-8

import os

import cookiecutter.find as find
import cookiecutter.generate as gen
import jinja2
from cookiecutter.config import DEFAULT_CONFIG as config
from cookiecutter.environment import StrictEnvironment
from cookiecutter.exceptions import NonTemplatedInputDirException

from ckan.cli.generate import remove_code_examples
from ckan.common import asbool


def recut():
    """
    Recreate setup.py so that we can edit keywords
    Remove unnecessary code examples
    """
    env = StrictEnvironment()
    # get context
    context = {}

    {% for key, value in cookiecutter.items() %}
    context["{{key}}"] = {{ value.__repr__() | safe }}
    {% endfor %}

    try:
        # cutting cookie from directory with template
        temp_dir = find.find_template(context['_repo_dir'], env)
    except NonTemplatedInputDirException as e:
        # template coming from Github
        # Hooks are passed through jinja2. raw will
        # Make sure `cookiecutter.project` isn't replaced
        {% raw %}
        temp_dir = os.path.join(config['cookiecutters_dir'],
                                'cookiecutter-ckan-extension',
                                '{{cookiecutter.project}}')
        {% endraw %}

    # Location for resulting file
    destination = os.getcwd()
    # name of template
    setup_template = 'setup.py'

    # Process keywords
    keywords = context['keywords'].strip().split()
    keywords = [keyword for keyword in keywords
                if keyword not in ('ckan', 'CKAN', 'A', 'space',
                                   'separated', 'list', 'of', 'keywords')]
    keywords.insert(0, 'CKAN')
    context['keywords'] = keywords

    # Double check 'project_shortname' and 'plugin_class_name'
    short_name = context['project'][8:].replace('-','_')
    if context['project_shortname'] != short_name:
        context['project_shortname'] = short_name

    plugin_class_name = '{}Plugin'.format(context['project_shortname']
                        .title().replace('_', ''))
    if context['plugin_class_name'] != plugin_class_name:
        context['plugin_class_name'] = plugin_class_name
    env.loader = jinja2.FileSystemLoader(temp_dir)
    gen.generate_file(project_dir=destination,
                      context={'cookiecutter': context},
                      infile=setup_template,
                      env=env)
    if not asbool(context['include_examples']):
        remove_code_examples(os.path.join(destination, 'ckanext', short_name))


if __name__ == '__main__':
    if '{{ cookiecutter._source }}' == 'local':
        recut()
