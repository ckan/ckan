# encoding: utf-8

from ckan.lib.helpers import url_for

import ckan.plugins as p

from nose.tools import assert_true
from ckan.tests import helpers, factories


class TestAudioView(helpers.FunctionalTestBase):
    _load_plugins = ['audio_view', 'image_view']

    @helpers.change_config('ckan.views.default_views', '')
    def test_view_shown_on_resource_page_with_audio_url(self):
        app = self._get_test_app()

        dataset = factories.Dataset()

        resource = factories.Resource(package_id=dataset['id'],
                                      format='wav')

        resource_view = factories.ResourceView(
            resource_id=resource['id'],
            view_type='audio_view',
            audio_url='http://example.wav')

        url = url_for('resource.read',
                      id=dataset['name'], resource_id=resource['id'])

        response = app.get(url)

        assert_true(resource_view['audio_url'] in response)
