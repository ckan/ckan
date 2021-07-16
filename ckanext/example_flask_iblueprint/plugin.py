# encoding: utf-8

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


def flask_request():
    '''A simple template with a helper that exists. Rendering with a helper
    shouldn't raise an exception.'''

    html = '''<!DOCTYPE html>
    <html>
        <head>
            <title>Hello from Flask</title>
        </head>
        <body> {{ request.params }} </body>
    </html>'''

    return render_template_string(html)


class ExampleFlaskIBlueprintPlugin(p.SingletonPlugin):
    '''
    An example IBlueprint plugin to demonstrate Flask routing from an
    extension.
    '''
    p.implements(p.IBlueprint)
    p.implements(p.IConfigurer)

    # IConfigurer

    def update_config(self, config):
        # Add extension templates directory
        p.toolkit.add_template_directory(config, 'templates')

    def get_blueprint(self):
        '''Return a Flask Blueprint object to be registered by the app.'''

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = 'templates'
        # Add plugin url rules to Blueprint object
        rules = [
            ('/hello_plugin', 'hello_plugin', hello_plugin),
            ('/', 'home', override_flask_home),
            ('/helper_not_here', 'helper_not_here', helper_not_here),
            ('/helper', 'helper_here', helper_here),
            ('/flask_request', 'flask_request', flask_request),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint
