from flask import Blueprint

import ckan.plugins as p


def hello_plugin():
    '''A simple view function'''
    return 'Hello World, this is served from an extension'


def override_pylons_about():
    '''A simple replacement for the pylons About page.'''
    return 'This is an about page served from an extention, ' \
        'overriding the pylons url.'


def override_flask_hello():
    '''A simple replacement for the flash Hello view function.'''
    return 'Hello World, this is served from an extension, ' \
        'overriding the flask url.'


class ExampleFlaskIRoutesPlugin(p.SingletonPlugin):
    '''
    An example IRoutes plugin to demonstrate Flask routing from an extension.
    '''
    p.implements(p.IRoutes, inherit=True)

    def get_blueprint(self):
        '''Return a Flask Blueprint object to be registered by the app.'''

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        # Add plugin url rules to Blueprint object
        rules = [
            ('/hello_plugin', 'hello_plugin', hello_plugin),
            ('/about', 'about', override_pylons_about),
            ('/hello', 'hello', override_flask_hello)
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint
