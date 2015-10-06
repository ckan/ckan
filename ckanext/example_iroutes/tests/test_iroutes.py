from nose.tools import assert_equal, assert_in

import ckan.tests.helpers as helpers
import ckan.plugins as plugins
from plugins import toolkit as tk

CONTROLLER = 'ckanext.example_iroutes.controller:DashboardController'


class TestIRoutes(object):

    @classmethod
    def setup_class(cls):
        super(TestIRoutes, cls).setup_class()
        plugins.load('example_iroutes')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iroutes')
        super(TestIRoutes, cls).teardown_class()

    def test_added_route(self):
        assert_equal(tk.url_for('main_dash'), '/dashboard/main')
        assert_equal(tk.url_for(controller=CONTROLLER, action='main'),
                     '/dashboard/main')


class TestIRoutesFunctional(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        super(TestIRoutesFunctional, cls).setup_class()
        plugins.load('example_iroutes')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iroutes')
        super(TestIRoutesFunctional, cls).teardown_class()

    def test_added_route(self):
        app = self._get_test_app()
        response = app.get('/ckan-admin/myext_config_one', status=200)
        assert_in('Main Dashboard', response.body)

