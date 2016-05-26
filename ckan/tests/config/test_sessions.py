from nose.tools import ok_

from flask import Blueprint
from flask import render_template
from flask import redirect as flask_redirect
from flask import url_for
from ckan.lib.base import redirect as pylons_redirect
from ckan.lib.base import render as pylons_render

import ckan.plugins as p
import ckan.tests.helpers as helpers
import ckan.lib.helpers as h


class TestCrossFlaskPylonsFlashMessages(helpers.FunctionalTestBase):
    '''
    Test that flash message set in the Pylons controller can be accessed by
    Flask views, and visa versa.
    '''

    def setup(self):
        self.app = helpers._get_test_app()
        self.flask_app = helpers.find_flask_app(self.app)

        # Install plugin and register its blueprint
        if not p.plugin_loaded('test_flash_plugin'):
            p.load('test_flash_plugin')
            plugin = p.get_plugin('test_flash_plugin')
            self.flask_app.register_blueprint(plugin.get_blueprint(),
                                              prioritise_rules=True)

    def test_flash_populated_by_flask_redirect_to_flask(self):
        '''
        Flash store is populated by Flask view is accessible by another Flask
        view.
        '''
        res = self.app.get(
            '/flask_add_flash_message_redirect_to_flask').follow()

        ok_("This is a success message populate by Flask" in res.body)

    def test_flash_populated_in_pylons_action_redirect_to_flask(self):
        '''
        Flash store is populated by pylons action is accessible by Flask view.
        '''
        res = self.app.get('/pylons_add_flash_message_redirect_view').follow()

        ok_("This is a success message populate by Pylons" in res.body)

    def test_flash_populated_in_flask_view_redirect_to_pylons(self):
        '''
        Flash store is populated by flask view is accessible by pylons action.
        '''
        res = self.app.get('/flask_add_flash_message_redirect_pylons').follow()

        ok_("This is a success message populate by Flask" in res.body)


class FlashMessagePlugin(p.SingletonPlugin):
    '''
    A Flask and Pylons compatible IRoutes plugin to add Flask views and Pylons
    actions to display flash messages.
    '''

    p.implements(p.IRoutes, inherit=True)

    def flash_message_view(self):
        '''Flask view that renders the flash message html template.'''
        return render_template('tests/flash_messages.html')

    def add_flash_message_view_redirect_to_flask(self):
        '''Add flash message, then redirect to Flask view to render it.'''
        h.flash_success("This is a success message populate by Flask")
        return flask_redirect(url_for('test_flash_plugin.flash_message_view'))

    def add_flash_message_view_redirect_to_pylons(self):
        '''Add flash message, then redirect to view that renders it'''
        h.flash_success("This is a success message populate by Flask")
        return flask_redirect('/pylons_view_flash_message')

    def get_blueprint(self):
        '''Return Flask Blueprint object to be registered by the Flask app.'''

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = 'templates'
        # Add plugin url rules to Blueprint object
        rules = [
            ('/flask_add_flash_message_redirect_to_flask', 'add_flash_message',
             self.add_flash_message_view_redirect_to_flask),
            ('/flask_add_flash_message_redirect_pylons',
             'add_flash_message_view_redirect_to_pylons',
             self.add_flash_message_view_redirect_to_pylons),
            ('/flask_view_flash_message', 'flash_message_view',
             self.flash_message_view),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint

    controller = \
        'ckan.tests.config.test_sessions:PylonsAddFlashMessageController'

    def before_map(self, _map):
        '''Update the pylons route map to be used by the Pylons app.'''
        _map.connect('/pylons_add_flash_message_redirect_view',
                     controller=self.controller,
                     action='add_flash_message_redirect')

        _map.connect('/pylons_view_flash_message',
                     controller=self.controller,
                     action='flash_message_action')
        return _map


class PylonsAddFlashMessageController(p.toolkit.BaseController):

    def flash_message_action(self):
        '''Pylons view to render flash messages in a template.'''
        return pylons_render('tests/flash_messages.html')

    def add_flash_message_redirect(self):
        # Adds a flash message and redirects to flask view
        h.flash_success('This is a success message populate by Pylons')
        return pylons_redirect('/flask_view_flash_message')
