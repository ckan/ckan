# encoding: utf-8

import pytest


@pytest.mark.ckan_config('ckan.plugins', 'stats')
@pytest.mark.usefixtures('with_plugins')
class TestStatsPlugin(object):
    def test_stats_available(self, app):
        resp = app.get('/stats')
        assert resp.status_code == 200
