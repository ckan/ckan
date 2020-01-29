# encoding: utf-8

import os
import json
import jinja2
import cookiecutter.find as find
import cookiecutter.generate as gen
from cookiecutter.config import DEFAULT_CONFIG as config
from cookiecutter.environment import StrictEnvironment
from cookiecutter.exceptions import NonTemplatedInputDirException
from cookiecutter.main import cookiecutter as c


def recut():
    """
        Recreate setup.py so that we can edit keywords
    """
    # template location
    try:
        # cutting cookie from directory with template
        temp_dir = find.find_template('..')
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

    # get context
    context = {{ cookiecutter | jsonify }}

    # Process keywords
    keywords = context['keywords'].strip().split()
    keywords = [keyword for keyword in keywords
                if keyword not in ('ckan', 'CKAN', 'A', 'space',
                                   'seperated', 'list', 'of', 'keywords')]
    keywords.insert(0, 'CKAN')
    keywords = u' '.join(keywords)
    context['keywords'] = keywords

    # Double check 'project_shortname' and 'plugin_class_name'
    short_name = context['project'][8:].replace('-','_')
    if context['project_shortname'] != short_name:
        context['project_shortname'] = short_name

    plugin_class_name = '{}Plugin'.format(context['project_shortname']
                        .title().replace('_', ''))
    if context['plugin_class_name'] != plugin_class_name:
        context['plugin_class_name'] = plugin_class_name

    # Recut cookie
    env = StrictEnvironment()
    env.loader = jinja2.FileSystemLoader(temp_dir)
    gen.generate_file(project_dir=destination,
                      infile=setup_template,
                      context={'cookiecutter': context},
                      env=env)


if __name__ == '__main__':
    context = {{ cookiecutter | jsonify }}
    if context['_source'] == 'local':
        recut()
