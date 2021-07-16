# -*- coding: utf-8 -*-

import pytest

import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "example_itemplatehelpers")
@pytest.mark.usefixtures("with_plugins")
def test_chained_helper():
    data = {"hello": "world"}
    assert '{"hello": "world"}' == tk.h.dump_json(data)
    assert 'Not today' == tk.h.dump_json(data, test_itemplatehelpers=True)
