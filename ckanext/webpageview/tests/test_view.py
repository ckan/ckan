# encoding: utf-8

import pytest
from ckan.lib.helpers import url_for

from ckan.tests import factories


@pytest.mark.ckan_config("ckan.plugins", "webpage_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestWebPageView(object):

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    def test_view_shown_on_resource_page(self, app):

        dataset = factories.Dataset()

        resource = factories.Resource(
            package_id=dataset["id"], url="http://some.website.html"
        )

        resource_view = factories.ResourceView(
            resource_id=resource["id"],
            view_type="webpage_view",
            page_url="http://some.other.website.html",
        )

        url = url_for(
            "resource.read", id=dataset["name"], resource_id=resource["id"]
        )

        response = app.get(url)

        assert resource_view["page_url"] in response
