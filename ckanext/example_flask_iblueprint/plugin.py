# encoding: utf-8

from flask import Blueprint
from flask import render_template, render_template_string

import ckan.plugins as p


def hello_plugin():
    u'''A simple view function'''
    return u'Hello World, this is served from an extension'


def override_pylons_about():
    u'''A simple replacement for the pylons About page.'''
    return render_template(u'about.html')


def override_pylons_about_with_core_template():
    u'''
    Override the pylons about controller to render the core about page
    template.
    '''
    return render_template(u'home/about.html')


def override_flask_hello():
    u'''A simple replacement for the flash Hello view function.'''
    html = u'''<!DOCTYPE html>
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

    u'''A simple template with a helper that doesn't exist. Rendering with a
    helper that doesn't exist causes server error.'''

    html = u'''<!DOCTYPE html>
    <html>
        <head>
            <title>Hello from Flask</title>
        </head>
        <body>Hello World, {{ h.nohere() }} no helper here</body>
    </html>'''

    return render_template_string(html)


def helper_here():

    u'''A simple template with a helper that exists. Rendering with a helper
    shouldn't raise an exception.'''

    html = u'''<!DOCTYPE html>
    <html>
        <head>
            <title>Hello from Flask</title>
        </head>
        <body>Hello World, helper here: {{ h.render_markdown('*hi*') }}</body>
    </html>'''

    return render_template_string(html)


class ExampleFlaskIBlueprintPlugin(p.SingletonPlugin):
    u'''
    An example IBlueprint plugin to demonstrate Flask routing from an
    extension.
    '''
    p.implements(p.IBlueprint)

    def get_blueprint(self):
        u'''Return a Flask Blueprint object to be registered by the app.'''

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # Add plugin url rules to Blueprint object
        rules = [
            (u'/hello_plugin', u'hello_plugin', hello_plugin),
            (u'/about', u'about', override_pylons_about),
            (u'/about_core', u'about_core',
                override_pylons_about_with_core_template),
            (u'/hello', u'hello', override_flask_hello),
            (u'/helper_not_here', u'helper_not_here', helper_not_here),
            (u'/helper', u'helper_here', helper_here),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint
