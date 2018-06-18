# encoding: utf-8

from ckan.lib.helpers import url_for

import ckan.plugins as p

from nose.tools import assert_true
from ckan.tests import helpers, factories


class TestImageView(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        super(TestImageView, cls).setup_class()

        if not p.plugin_loaded('image_view'):
            p.load('image_view')

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

        super(TestImageView, cls).teardown_class()

        helpers.reset_db()

    @helpers.change_config('ckan.views.default_views', '')
    def test_view_shown_on_resource_page_with_image_url(self):
        app = self._get_test_app()

        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset['id'],
                                      format='png')

        resource_view = factories.ResourceView(
            resource_id=resource['id'],
            image_url='http://some.image.png')

        url = url_for(controller='package', action='resource_read',
                      id=dataset['name'], resource_id=resource['id'])

        response = app.get(url)

        assert_true(resource_view['image_url'] in response)
