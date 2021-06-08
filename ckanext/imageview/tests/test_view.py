# encoding: utf-8

import pytest
from ckan.lib.helpers import url_for
from ckan.tests import factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config('ckan.views.default_views', '')
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_view_shown_on_resource_page_with_image_url(app):

    dataset = factories.Dataset()

    resource = factories.Resource(package_id=dataset['id'],
                                  format='png')

    resource_view = factories.ResourceView(
        resource_id=resource['id'],
        image_url='http://some.image.png')

    url = url_for('{}_resource.read'.format(dataset['type']),
                  id=dataset['name'], resource_id=resource['id'])

    response = app.get(url)

    assert helpers.body_contains(response, resource_view['image_url'])
