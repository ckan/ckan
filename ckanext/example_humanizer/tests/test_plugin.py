# -*- coding: utf-8 -*-
import pytest
import bs4

import ckan.tests.factories as factories


@pytest.mark.ckan_config("ckan.plugins", "example_humanizer")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestExampleHumanizer(object):
    @pytest.mark.parametrize("url, breadcrumb, button", [
        ('/dataset', "Datasets", "Create new Dataset"),
        ('/organization', "Organizations", "Create new Organization"),
        ('/group', "Groups", "Create new Group"),
        ('/custom_group', "Custom groups", "Create new Custom group"),
    ])
    def test_original_translations(self, app, url, breadcrumb, button):
        user = factories.User(password="correct123")
        user_token = factories.APIToken(user=user["name"])
        headers = {"Authorization": user_token["token"]}
        res = app.get(url, headers=headers)
        page = bs4.BeautifulSoup(res.body)
        assert page.select_one('.toolbar .active').text == breadcrumb
        assert page.select_one('.content_action .btn-primary').text.strip() == button
