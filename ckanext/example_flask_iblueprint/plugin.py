# encoding: utf-8

from ckan.common import CKANConfig
from flask import Blueprint
from flask import render_template_string

import ckan.plugins as p


def hello_plugin():
    '''A simple view function'''
    return 'Hello World, this is served from an extension'


def override_flask_home():
    '''A simple replacement for the flash Home view function.'''
    html = '''<!DOCTYPE html>
<html>
    <head>
        <title>Hello from Flask</title>
    </head>
    <body>
    Hello World, this is served from an extension, overriding the flask url.
    </body>
</html>'''

    return render_template_string(html)


def helper_not_here():
    '''A simple template with a helper that doesn't exist. Rendering with a
    helper that doesn't exist causes server error.'''

    html = '''<!DOCTYPE html>
    <html>
        <head>
            <title>Hello from Flask</title>
        </head>
        <body>Hello World, {{ h.nohere() }} no helper here</body>
    </html>'''

    return render_template_string(html)


def helper_here():
    '''A simple template with a helper that exists. Rendering with a helper
    shouldn't raise an exception.'''

    html = '''<!DOCTYPE html>
    <html>
        <head>
            <title>Hello from Flask</title>
        </head>
        <body>Hello World, helper here: {{ h.render_markdown('*hi*') }}</body>
    </html>'''

    return render_template_string(html)


def another_blueprint():
    '''A simple view function'''
    return 'Hello World, this is served from the second blueprint'


class ExampleFlaskIBlueprintPlugin(p.SingletonPlugin):
    '''
    An example IBlueprint plugin to demonstrate Flask routing from an
    extension.
    '''
    p.implements(p.IBlueprint)
    p.implements(p.IConfigurer)

    # IConfigurer

    def update_config(self, config: CKANConfig):
        # Add extension templates directory
        p.toolkit.add_template_directory(config, 'templates')

    def get_blueprint(self):
        '''Return blueprints to be registered by the app.

        This method can return either a Flask Blueprint object or
        a list of Flask Blueprint objects.
        '''

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = 'templates'
        # Add plugin url rules to Blueprint object
        rules = [
            ('/hello_plugin', 'hello_plugin', hello_plugin),
            ('/', 'home', override_flask_home),
            ('/helper_not_here', 'helper_not_here', helper_not_here),
            ('/helper', 'helper_here', helper_here),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        # Create a second Blueprint for plugin if needed
        blueprint_2 = Blueprint('blueprint_2', self.__module__)
        blueprint_2.add_url_rule(
            '/another_blueprint', 'another_blueprint', another_blueprint
        )

        return [blueprint, blueprint_2]
