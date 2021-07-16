# -*- coding: utf-8 -*-
import pytest
import six
import bs4

import ckan.tests.factories as factories


@pytest.mark.ckan_config("ckan.plugins", "example_humanizer")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestExampleHumanizer(object):
    @pytest.mark.parametrize("url, breadcrumb, button", [
        ('/dataset', "Datasets", "Add Dataset"),
        ('/organization', "Organizations", "Add Organization"),
        ('/group', "Groups", "Add Group"),
        ('/custom_group', "Custom groups", "Create new Custom group"),
    ])
    def test_original_translations(self, app, url, breadcrumb, button):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        resp = app.get(url, extra_environ=env)
        page = bs4.BeautifulSoup(resp.body)
        assert page.select_one('.toolbar .active').text == breadcrumb
        btn = page.select_one('.page_primary_action').text.strip() == button
