# -*- coding: utf-8 -*-
import pytest
import six
import bs4

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config(u"ckan.plugins", u"example_humanizer")
@pytest.mark.usefixtures(u"clean_db", u"with_plugins", u"with_request_context")
class TestExampleHumanizer(object):
    @pytest.mark.parametrize(u"url, breadcrumb, button", [
        (u'/dataset', u"Datasets", u"Add Dataset"),
        (u'/organization', u"Organizations", u"Add Organization"),
        (u'/group', u"Groups", u"Add Group"),
        (u'/custom_group', u"Custom groups", u"Create new Custom group"),
    ])
    def test_original_translations(self, app, url, breadcrumb, button):
        user = factories.User(password="correct123")
        identity = {"login": user["name"], "password": "correct123"}
        helpers.login_user(app, identity)
        resp = app.get(url)
        page = bs4.BeautifulSoup(resp.body)
        assert page.select_one(u'.toolbar .active').text == breadcrumb
        page.select_one(u'.page_primary_action').text.strip() == button
