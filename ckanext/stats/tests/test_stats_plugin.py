# encoding: utf-8

import pytest


@pytest.mark.ckan_config(u'ckan.plugins', u'stats')
@pytest.mark.usefixtures(u'with_plugins')
class TestStatsPlugin(object):
    def test_stats_available(self, app):
        resp = app.get(u'/stats')
        assert resp.status_code == 200
