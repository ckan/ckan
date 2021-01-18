# encoding: utf-8

import pytest
from ckan.lib.helpers import url_for
from ckan.tests import factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config(u'ckan.views.default_views', u'')
@pytest.mark.ckan_config(u'ckan.plugins', u'pdf_view')
@pytest.mark.usefixtures(u'clean_db', u'with_plugins')
def test_view_shown_on_resource_page_with_pdf_url(app):

    dataset = factories.Dataset()

    resource = factories.Resource(package_id=dataset['id'],
                                  format='pdf')

    resource_view = factories.ResourceView(
        resource_id=resource['id'],
        view_type=u'pdf_view',
        pdf_url=u'https://example/document.pdf')

    url = url_for(u'{}_resource.read'.format(dataset['type']),
                  id=dataset['name'], resource_id=resource['id'])

    response = app.get(url)

    assert helpers.body_contains(response, resource_view['pdf_url'])
