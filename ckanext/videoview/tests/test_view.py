# encoding: utf-8

import pytest

from ckan.lib.helpers import url_for
from ckan.tests import factories


@pytest.mark.ckan_config('ckan.views.default_views', '')
@pytest.mark.ckan_config("ckan.plugins", "video_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_view_shown_on_resource_page_with_video_url(app):

    dataset = factories.Dataset()

    resource = factories.Resource(package_id=dataset['id'],
                                  format='mp4')

    resource_view = factories.ResourceView(
        resource_id=resource['id'],
        view_type='video_view',
        video_url='https://example/video.mp4')

    url = url_for('{}_resource.read'.format(dataset['type']),
                  id=dataset['name'], resource_id=resource['id'])

    response = app.get(url)

    assert resource_view['video_url'] in response
