# encoding: utf-8
import pytest

from ckan.lib.helpers import url_for
from ckan.tests import factories


@pytest.mark.ckan_config('ckan.views.default_views', '')
@pytest.mark.ckan_config("ckan.plugins", "audio_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_view_shown_on_resource_page_with_audio_url(app):

    dataset = factories.Dataset()

    resource = factories.Resource(package_id=dataset['id'],
                                  format='wav')

    resource_view = factories.ResourceView(
        resource_id=resource['id'],
        view_type='audio_view',
        audio_url='http://example.wav')

    url = url_for('{}_resource.read'.format(dataset['type']),
                  id=dataset['name'], resource_id=resource['id'])

    response = app.get(url)

    assert resource_view['audio_url'] in response
