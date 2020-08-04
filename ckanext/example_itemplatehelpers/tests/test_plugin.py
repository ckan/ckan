# -*- coding: utf-8 -*-

import pytest

import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config(u"ckan.plugins", u"example_itemplatehelpers")
@pytest.mark.usefixtures(u"with_plugins")
def test_chained_helper():
    data = {u"hello": u"world"}
    assert u'{"hello": "world"}' == tk.h.dump_json(data)
    assert u'Not today' == tk.h.dump_json(data, test_itemplatehelpers=True)
