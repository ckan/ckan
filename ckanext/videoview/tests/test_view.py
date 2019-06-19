# encoding: utf-8

from ckan.lib.helpers import url_for

import ckan.plugins as p

from nose.tools import assert_true
from ckan.tests import helpers, factories


class TestImageView(helpers.FunctionalTestBase):
    _load_plugins = ['video_view']

    @helpers.change_config('ckan.views.default_views', '')
    def test_view_shown_on_resource_page_with_video_url(self):
        app = self._get_test_app()

        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset['id'],
                                      format='mp4')

        resource_view = factories.ResourceView(
            resource_id=resource['id'],
            video_url='http://some.video.mp4')

        url = url_for('resource.read',
                      id=dataset['name'], resource_id=resource['id'])

        response = app.get(url)

        assert_true(resource_view['video_url'] in response)
