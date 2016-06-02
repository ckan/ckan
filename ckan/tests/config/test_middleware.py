# encoding: utf-8

import mock
import wsgiref
import nose
from nose.tools import assert_equals, assert_not_equals, eq_
from routes import url_for

import ckan.plugins as p
import ckan.tests.helpers as helpers

from ckan.config.middleware import AskAppDispatcherMiddleware, CKANFlask
from ckan.controllers.partyline import PartylineController


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

    def test_invitations_are_sent(self):

        with mock.patch.object(AskAppDispatcherMiddleware,
                               'send_invitations') as \
                mock_send_invitations:

            # This will create the whole WSGI stack
            helpers._get_test_app()

            assert mock_send_invitations.called
            eq_(len(mock_send_invitations.call_args[0]), 1)

            eq_(sorted(mock_send_invitations.call_args[0][0].keys()),
                ['flask_app', 'pylons_app'])

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

        with mock.patch.object(PartylineController, 'can_handle_request') as \
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
            mock_ask_around.assert_called_with('can_handle_request', environ)

    def test_ask_around_flask_core_route_get(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/hello',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around('can_handle_request', environ)

        # Even though this route is defined in Flask, there is catch all route
        # in Pylons for all requests to point arbitrary urls to templates with
        # the same name, so we get two positive answers
        eq_(len(answers), 2)
        eq_([a[0] for a in answers], [True, True])
        eq_(sorted([a[1] for a in answers]), ['flask_app', 'pylons_app'])
        # TODO: check origin (core/extension) when that is in place

    def test_ask_around_flask_core_route_post(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/hello',
            'REQUEST_METHOD': 'POST',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around('can_handle_request', environ)

        # Even though this route is defined in Flask, there is catch all route
        # in Pylons for all requests to point arbitrary urls to templates with
        # the same name, so we get two positive answers
        eq_(len(answers), 2)
        eq_([a[0] for a in answers], [True, True])
        eq_(sorted([a[1] for a in answers]), ['flask_app', 'pylons_app'])
        # TODO: check origin (core/extension) when that is in place

    def test_ask_around_pylons_core_route_get(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/dataset',
            'REQUEST_METHOD': 'GET',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around('can_handle_request', environ)

        eq_(len(answers), 1)
        eq_(answers[0][0], True)
        eq_(answers[0][1], 'pylons_app')
        eq_(answers[0][2], 'core')

    def test_ask_around_pylons_core_route_post(self):

        app = self._get_test_app()

        # We want our CKAN app, not the WebTest one
        app = app.app

        environ = {
            'PATH_INFO': '/dataset/new',
            'REQUEST_METHOD': 'POST',
        }
        wsgiref.util.setup_testing_defaults(environ)

        answers = app.ask_around('can_handle_request', environ)

        eq_(len(answers), 1)
        eq_(answers[0][0], True)
        eq_(answers[0][1], 'pylons_app')
        eq_(answers[0][2], 'core')

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

        answers = app.ask_around('can_handle_request', environ)

        eq_(len(answers), 1)
        eq_(answers[0][0], True)
        eq_(answers[0][1], 'pylons_app')
        eq_(answers[0][2], 'extension')

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

        answers = app.ask_around('can_handle_request', environ)

        eq_(len(answers), 1)
        eq_(answers[0][0], True)
        eq_(answers[0][1], 'pylons_app')
        eq_(answers[0][2], 'extension')

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

        answers = app.ask_around('can_handle_request', environ)

        # We are going to get an answer from Pylons, but just because it will
        # match the catch-all template route, hence the `core` origin.
        eq_(len(answers), 1)
        eq_(answers[0][0], True)
        eq_(answers[0][1], 'pylons_app')
        eq_(answers[0][2], 'core')

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

        answers = app.ask_around('can_handle_request', environ)

        eq_(len(answers), 1)
        eq_(answers[0][0], True)
        eq_(answers[0][1], 'pylons_app')
        eq_(answers[0][2], 'extension')

        p.unload('test_routing_plugin')

    def test_ask_around_flask_core_and_pylons_extension_route(self):

        # TODO: re-enable when we have a way for Flask extensions to add routes
        raise nose.SkipTest()

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

        answers = app.ask_around('can_handle_request', environ)
        answers = sorted(answers, key=lambda a: a[1])

        eq_(len(answers), 2)
        eq_([a[0] for a in answers], [True, True])
        eq_([a[1] for a in answers], ['flask_app', 'pylons_app'])

        # TODO: we still can't distinguish between Flask core and extension
        # eq_(answers[0][2], 'extension')

        eq_(answers[1][2], 'extension')

        p.unload('test_routing_plugin')

    def test_flask_core_route_is_served_by_flask(self):

        app = self._get_test_app()

        res = app.get('/hello')

        eq_(res.environ['ckan.app'], 'flask_app')

    # TODO: test flask extension route

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

        res = app.get('/api/action/status_show')

        eq_(res.environ['ckan.app'], 'flask_app')


class MockRoutingPlugin(p.SingletonPlugin):

    p.implements(p.IRoutes)

    controller = 'ckan.tests.config.test_middleware:MockPylonsController'

    def before_map(self, _map):

        _map.connect('/from_pylons_extension_before_map',
                     controller=self.controller, action='view')

        _map.connect('/from_pylons_extension_before_map_post_only',
                     controller=self.controller, action='view',
                     conditions={'method': 'POST'})
        # This one conflicts with a core Flask route
        _map.connect('/pylons_and_flask',
                     controller=self.controller, action='view')

        return _map

    def after_map(self, _map):

        _map.connect('/from_pylons_extension_after_map',
                     controller=self.controller, action='view')

        return _map


class MockPylonsController(p.toolkit.BaseController):

    def view(self):
        return 'Hello World, this is served from a Pylons extension'
