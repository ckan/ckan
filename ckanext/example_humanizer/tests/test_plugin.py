# -*- coding: utf-8 -*-
import pytest
import six
import bs4

import ckan.plugins.toolkit as tk
import ckan.tests.factories as factories


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
        user = factories.User()
        env = {u"REMOTE_USER": six.ensure_str(user[u"name"])}
        resp = app.get(url, extra_environ=env)
        page = bs4.BeautifulSoup(resp.body)
        assert page.select_one(u'.toolbar .active').text == breadcrumb
        btn = page.select_one(u'.page_primary_action').text.strip() == button
