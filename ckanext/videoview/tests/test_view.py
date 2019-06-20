# encoding: utf-8

from ckan.lib.helpers import url_for

import ckan.plugins as p

from nose.tools import assert_true
from ckan.tests import helpers, factories


class TestVideoView(helpers.FunctionalTestBase):
    # Tests using ResourceView need to import image_view too
    _load_plugins = [u'image_view', u'video_view']

    @helpers.change_config(u'ckan.views.default_views', u'')
    def test_view_shown_on_resource_page_with_video_url(self):
        app = self._get_test_app()

        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset[u'id'],
                                      format=u'video/mp4',
                                      url=u'http://some.video.mp4')

        resource_view = factories.ResourceView(
            resource_id=resource[u'id'],
            view_type=u'video_view')

        url = url_for(u'resource.read',
                      id=dataset[u'name'],
                      resource_id=resource[u'id'],
                      video_url=u'http://some.video.mp4')

        response = app.get(url)

        assert_true(resource_view[u'video_url'] in response)
