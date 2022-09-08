# -*- coding: utf-8 -*-
import pytest
import bs4

import ckan.tests.factories as factories


@pytest.mark.ckan_config(u"ckan.plugins", u"example_humanizer")
@pytest.mark.usefixtures(u"non_clean_db", u"with_plugins")
class TestExampleHumanizer(object):
    @pytest.mark.parametrize(u"url, breadcrumb, button", [
        (u'/dataset', u"Datasets", u"Add Dataset"),
        (u'/organization', u"Organizations", u"Add Organization"),
        (u'/group', u"Groups", u"Add Group"),
        (u'/custom_group', u"Custom groups", u"Create new Custom group"),
    ])
    def test_original_translations(self, app, url, breadcrumb, button):
        user = factories.User(password="correct123")
        user_token = factories.APIToken(user=user["name"])
        env = {"Authorization": user_token["token"]}
        res = app.get(url, environ_overrides=env)
        page = bs4.BeautifulSoup(res.body)
        assert page.select_one(u'.toolbar .active').text == breadcrumb
        page.select_one(u'.page_primary_action').text.strip() == button
