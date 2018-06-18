# encoding: utf-8

from ckan.lib.helpers import url_for

import ckan.plugins as p

from nose.tools import assert_true
from ckan.tests import helpers, factories


class TestWebPageView(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        super(TestWebPageView, cls).setup_class()

        if not p.plugin_loaded('webpage_view'):
            p.load('webpage_view')

    @classmethod
    def teardown_class(cls):
        p.unload('webpage_view')

        super(TestWebPageView, cls).teardown_class()

        helpers.reset_db()

    @helpers.change_config('ckan.views.default_views', '')
    def test_view_shown_on_resource_page(self):
        app = self._get_test_app()

        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset['id'],
                                      url='http://some.website.html')

        resource_view = factories.ResourceView(
            resource_id=resource['id'],
            view_type='webpage_view',
            page_url='http://some.other.website.html',)

        url = url_for(controller='package', action='resource_read',
                      id=dataset['name'], resource_id=resource['id'])

        response = app.get(url)

        assert_true(resource_view['page_url'] in response)
