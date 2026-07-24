# -*- coding: utf-8 -*-

import datetime

import pytest

import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
class TestActivityListSelect(object):
    def test_simple(self):
        pkg_activity = {
            "id": "id1",
            "timestamp": datetime.datetime(2018, 2, 1, 10, 58, 59),
        }

        out = tk.h.activity_list_select([pkg_activity], "")

        html = out[0]
        assert (
            str(html)
            == '<option value="id1" >February 1, 2018, 10:58:59\u202fAM UTC</option>'
        )
        assert hasattr(html, "__html__")  # shows it is safe Markup

    def test_selected(self):
        pkg_activity = {
            "id": "id1",
            "timestamp": datetime.datetime(2018, 2, 1, 10, 58, 59),
        }

        out = tk.h.activity_list_select([pkg_activity], "id1")

        html = out[0]
        assert (
            str(html)
            == '<option value="id1" selected>February 1, 2018, 10:58:59\u202fAM UTC</option>'
        )
        assert hasattr(html, "__html__")  # shows it is safe Markup

    def test_escaping(self):
        pkg_activity = {
            "id": '">',  # hacked somehow
            "timestamp": datetime.datetime(2018, 2, 1, 10, 58, 59),
        }

        out = tk.h.activity_list_select([pkg_activity], "")

        html = out[0]
        assert str(html).startswith('<option value="&#34;&gt;" >')
