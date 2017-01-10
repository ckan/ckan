# encoding: utf-8

import mock
import wsgiref
from nose.tools import assert_equals, assert_not_equals, eq_, assert_raises
from routes import url_for
from flask import Blueprint
import flask

import ckan.model as model
import ckan.plugins as p
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
from ckan.common import config

from ckan.config.middleware import AskAppDispatcherMiddleware
from ckan.config.middleware.flask_app import CKANFlask
from ckan.config.middleware.pylons_app import CKANPylonsApp


class TestPylonsResponseCleanupMiddleware(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, config):
        config['ckan.use_pylons_response_cleanup_middleware'] = True

    def test_homepage_with_middleware_activated(self):
        '''Test the home page renders with the middleware activated

        We are just testing the home page renders without any troubles and that
        the middleware has not done anything strange to the response string'''
        app = self._get_test_app()
        response = app.get(url=url_for(controller='home', action='index'))

        assert_equals(200, response.status_int)
        # make sure we haven't overwritten the response too early.
        assert_not_equals(
            'response cleared by pylons response cleanup middleware',
            response.body
        )


class TestAppDispatcherPlain(object):
    '''
    These tests need the test app to be created at specific times to not affect
    the mocks, so they don't extend FunctionalTestBase
    '''

    def test_flask_can_handle_request_is_called_with_environ(self):

        with mock.patch.object(CKANFlask, 'can_handle_request') as \
                mock_can_handle_request:
            # We need set this otherwise the mock object is returned
            mock_can_handle_request.return_value = (False, 'flask_app')

            app = helpers._get_test_app()
            # We want our CKAN app, not the WebTest one
            ckan_app = app.app

            environ = {
                'PATH_INFO': '/',
            }
            wsgiref.util.setup_testing_defaults(environ)
            start_response = mock.MagicMock()

            ckan_app(environ, start_response)

            assert mock_can_handle_request.called_with(environ)

    def test_pylons_can_handle_request_is_called_with_environ(self):

        with mock.patch.object(CKANPylonsApp, 'can_handle_request') as \
                mock_can_handle_request:

            # We need set this otherwise the mock object is returned
            mock_can_handle_request.return_value = (True, 'pylons_app', 'core')

            app = helpers._get_test_app()
            # We want our CKAN app, not the WebTest one
            ckan_app = app.app

            environ = {
                'PATH_INFO': '/',
            }
            wsgiref.util.setup_testing_defaults(environ)
            start_response = mock.MagicMock()

            ckan_app(environ, start_response)

            assert mock_can_handle_request.called_with(environ)


class TestAppDispatcher(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        super(TestAppDispatcher, cls).setup_class()

        # Add a custom route to the Flask app
        app = cls._get_test_app()

        flask_app = app.flask_app

        def test_view():
            return 'This was served from Flask'

        # This endpoint is defined both in Flask and in Pylons core
        flask_app.add_url_rule('/about', view_func=test_view)

        # This endpoint is defined both in Flask and a Pylons extension
        flask_app.add_url_rule('/pylons_and_flask', view_func=test_view)

    def test_ask_around_is_called(self):

        app = self._get_test_app()
        with mock.patch.object(AskAppDispatcherMiddleware, 'ask_around') as \
                mock_ask_around:
            app.get('/')

            assert mock_ask_around.called

    def test_ask_around_is_called_with_args(self):

        app = self._get_test_app()
        ckan_app = app.app

        environ = {}
        start_response = mock.MagicMock()
        wsgiref.util.setup_testing_defaults(environ)

        with mock.patch.object(AskAppDispatcherMiddleware, 'ask_around') as \
                mock_ask_around:

            ckan_app(environ, start_response)
            assert mock_ask_around.called
            mock_ask_around.assert_called_with(environ)

    def test_ask_around_flask_core_route_get(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/hello',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        # Even though this route is defined in Flask, there is catch all route
        # in Pylons for all requests to point arbitrary urls to templates with
        # the same name, so we get two positive answers
        eq_(answers, [(True, 'flask_app', 'core'),
                      (True, 'pylons_app', 'core')])

    def test_ask_around_flask_core_route_post(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/hello',
            'REQUEST_METHOD': 'POST',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        # Even though this route is defined in Flask, there is catch all route
        # in Pylons for all requests to point arbitrary urls to templates with
        # the same name, so we get two positive answers
        eq_(answers, [(True, 'flask_app', 'core'),
                      (True, 'pylons_app', 'core')])

    def test_ask_around_pylons_core_route_get(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/dataset',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        eq_(answers, [(False, 'flask_app'), (True, 'pylons_app', 'core')])

    def test_ask_around_pylons_core_route_post(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/dataset/new',
            'REQUEST_METHOD': 'POST',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        eq_(answers, [(False, 'flask_app'), (True, 'pylons_app', 'core')])

    def test_ask_around_pylons_extension_route_get_before_map(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/from_pylons_extension_before_map',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        eq_(answers, [(False, 'flask_app'), (True, 'pylons_app', 'extension')])

        p.unload('test_routing_plugin')

    def test_ask_around_pylons_extension_route_post(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/from_pylons_extension_before_map_post_only',
            'REQUEST_METHOD': 'POST',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        eq_(answers, [(False, 'flask_app'), (True, 'pylons_app', 'extension')])

        p.unload('test_routing_plugin')

    def test_ask_around_pylons_extension_route_post_using_get(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/from_pylons_extension_before_map_post_only',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        # We are going to get an answer from Pylons, but just because it will
        # match the catch-all template route, hence the `core` origin.
        eq_(answers, [(False, 'flask_app'), (True, 'pylons_app', 'core')])

        p.unload('test_routing_plugin')

    def test_ask_around_pylons_extension_route_get_after_map(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/from_pylons_extension_after_map',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)

        eq_(answers, [(False, 'flask_app'), (True, 'pylons_app', 'extension')])

        p.unload('test_routing_plugin')

    def test_ask_around_flask_core_and_pylons_extension_route(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/pylons_and_flask',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around(environ)
        answers = sorted(answers, key=lambda a: a[1])

        eq_(answers, [(True, 'flask_app', 'core'),
                      (True, 'pylons_app', 'extension')])

        p.unload('test_routing_plugin')

    def test_flask_core_route_is_served_by_flask(self):

        app = self._get_test_app()

        res = app.get('/hello')

        eq_(res.environ['ckan.app'], 'flask_app')

    def test_flask_extension_route_is_served_by_flask(self):

        app = self._get_test_app()

        # Install plugin and register its blueprint
        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')
            plugin = p.get_plugin('test_routing_plugin')
            app.flask_app.register_extension_blueprint(plugin.get_blueprint())

        res = app.get('/simple_flask')

        eq_(res.environ['ckan.app'], 'flask_app')

        p.unload('test_routing_plugin')

    def test_pylons_core_route_is_served_by_pylons(self):

        app = self._get_test_app()

        res = app.get('/dataset')

        eq_(res.environ['ckan.app'], 'pylons_app')

    def test_pylons_extension_route_is_served_by_pylons(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        res = app.get('/from_pylons_extension_before_map')

        eq_(res.environ['ckan.app'], 'pylons_app')
        eq_(res.body, 'Hello World, this is served from a Pylons extension')

        p.unload('test_routing_plugin')

    def test_flask_core_and_pylons_extension_route_is_served_by_pylons(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        res = app.get('/pylons_and_flask')

        eq_(res.environ['ckan.app'], 'pylons_app')
        eq_(res.body, 'Hello World, this is served from a Pylons extension')

        p.unload('test_routing_plugin')

    def test_flask_core_and_pylons_core_route_is_served_by_flask(self):
        '''
        This should never happen in core, but just in case
        '''
        app = self._get_test_app()

        res = app.get('/about')

        eq_(res.environ['ckan.app'], 'flask_app')
        eq_(res.body, 'This was served from Flask')


class TestFlaskUserIdentifiedInRequest(helpers.FunctionalTestBase):

    '''Flask identifies user during each request.

    Flask route provided by test.helpers.SimpleFlaskPlugin.
    '''

    @classmethod
    def setup_class(cls):
        super(TestFlaskUserIdentifiedInRequest, cls).setup_class()
        cls.app = cls._get_test_app()
        cls.flask_app = cls.app.flask_app

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')
            plugin = p.get_plugin('test_routing_plugin')
            cls.flask_app.register_extension_blueprint(
                plugin.get_blueprint())

    @classmethod
    def teardown_class(cls):
        super(TestFlaskUserIdentifiedInRequest, cls).teardown_class()
        p.unload('test_routing_plugin')

    def test_user_objects_in_g_normal_user(self):
        '''
        A normal logged in user request will have expected user objects added
        to request.
        '''
        user = factories.User()
        test_user_obj = model.User.by_name(user['name'])

        with self.flask_app.app_context():
            self.app.get(
                '/simple_flask',
                extra_environ={'REMOTE_USER': user['name'].encode('ascii')},)
            eq_(flask.g.user, user['name'])
            eq_(flask.g.userobj, test_user_obj)
            eq_(flask.g.author, user['name'])
            eq_(flask.g.remote_addr, 'Unknown IP Address')

    def test_user_objects_in_g_anon_user(self):
        '''
        An anon user request will have expected user objects added to request.
        '''
        with self.flask_app.app_context():
            self.app.get(
                '/simple_flask',
                extra_environ={'REMOTE_USER': ''},)
            eq_(flask.g.user, '')
            eq_(flask.g.userobj, None)
            eq_(flask.g.author, 'Unknown IP Address')
            eq_(flask.g.remote_addr, 'Unknown IP Address')

    def test_user_objects_in_g_sysadmin(self):
        '''
        A sysadmin user request will have expected user objects added to
        request.
        '''
        user = factories.Sysadmin()
        test_user_obj = model.User.by_name(user['name'])

        with self.flask_app.app_context():
            self.app.get(
                '/simple_flask',
                extra_environ={'REMOTE_USER': user['name'].encode('ascii')},)
            eq_(flask.g.user, user['name'])
            eq_(flask.g.userobj, test_user_obj)
            eq_(flask.g.author, user['name'])
            eq_(flask.g.remote_addr, 'Unknown IP Address')


class TestPylonsUserIdentifiedInRequest(helpers.FunctionalTestBase):

    '''Pylons identifies user during each request.

    Using a route setup via an extension to ensure we're always testing a
    Pylons-flavoured request.
    '''

    def test_user_objects_in_c_normal_user(self):
        '''
        A normal logged in user request will have expected user objects added
        to request.
        '''
        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()
        user = factories.User()
        test_user_obj = model.User.by_name(user['name'])

        resp = app.get(
            '/from_pylons_extension_before_map',
            extra_environ={'REMOTE_USER': user['name'].encode('ascii')})

        # tmpl_context available on response
        eq_(resp.tmpl_context.user, user['name'])
        eq_(resp.tmpl_context.userobj, test_user_obj)
        eq_(resp.tmpl_context.author, user['name'])
        eq_(resp.tmpl_context.remote_addr, 'Unknown IP Address')

        p.unload('test_routing_plugin')

    def test_user_objects_in_c_anon_user(self):
        '''
        An anon user request will have expected user objects added to request.
        '''
        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()

        resp = app.get(
            '/from_pylons_extension_before_map',
            extra_environ={'REMOTE_USER': ''})

        # tmpl_context available on response
        eq_(resp.tmpl_context.user, '')
        eq_(resp.tmpl_context.userobj, None)
        eq_(resp.tmpl_context.author, 'Unknown IP Address')
        eq_(resp.tmpl_context.remote_addr, 'Unknown IP Address')

        p.unload('test_routing_plugin')

    def test_user_objects_in_c_sysadmin(self):
        '''
        A sysadmin user request will have expected user objects added to
        request.
        '''
        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        app = self._get_test_app()
        user = factories.Sysadmin()
        test_user_obj = model.User.by_name(user['name'])

        resp = app.get(
            '/from_pylons_extension_before_map',
            extra_environ={'REMOTE_USER': user['name'].encode('ascii')})

        # tmpl_context available on response
        eq_(resp.tmpl_context.user, user['name'])
        eq_(resp.tmpl_context.userobj, test_user_obj)
        eq_(resp.tmpl_context.author, user['name'])
        eq_(resp.tmpl_context.remote_addr, 'Unknown IP Address')

        p.unload('test_routing_plugin')


class MockRoutingPlugin(p.SingletonPlugin):

    p.implements(p.IRoutes)
    p.implements(p.IBlueprint)

    controller = 'ckan.tests.config.test_middleware:MockPylonsController'

    def before_map(self, _map):

        _map.connect('/from_pylons_extension_before_map',
                     controller=self.controller, action='view')

        _map.connect('/from_pylons_extension_before_map_post_only',
                     controller=self.controller, action='view',
                     conditions={'method': 'POST'})
        # This one conflicts with an extension Flask route
        _map.connect('/pylons_and_flask',
                     controller=self.controller, action='view')

        # This one conflicts with a core Flask route
        _map.connect('/hello',
                     controller=self.controller, action='view')

        return _map

    def after_map(self, _map):

        _map.connect('/from_pylons_extension_after_map',
                     controller=self.controller, action='view')

        return _map

    def get_blueprint(self):
        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        # Add plugin url rule to Blueprint object
        blueprint.add_url_rule('/pylons_and_flask', 'flask_plugin_view',
                               flask_plugin_view)

        blueprint.add_url_rule('/simple_flask', 'flask_plugin_view',
                               flask_plugin_view)

        return blueprint


def flask_plugin_view():
    return 'Hello World, this is served from a Flask extension'


class MockPylonsController(p.toolkit.BaseController):

    def view(self):
        return 'Hello World, this is served from a Pylons extension'


class TestSecretKey(object):

    @helpers.change_config('SECRET_KEY', 'super_secret_stuff')
    def test_secret_key_is_used_if_present(self):

        app = helpers._get_test_app()

        eq_(app.flask_app.config['SECRET_KEY'],
            u'super_secret_stuff')

    @helpers.change_config('SECRET_KEY', None)
    def test_beaker_secret_is_used_by_default(self):

        app = helpers._get_test_app()

        eq_(app.flask_app.config['SECRET_KEY'],
            config['beaker.session.secret'])

    @helpers.change_config('SECRET_KEY', None)
    @helpers.change_config('beaker.session.secret', None)
    def test_no_beaker_secret_crashes(self):

        assert_raises(ValueError, helpers._get_test_app)

        # TODO: When Pylons is finally removed, we should test for
        # RuntimeError instead (thrown on `make_flask_stack`)
