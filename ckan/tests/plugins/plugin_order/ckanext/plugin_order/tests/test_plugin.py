# -*- coding: utf-8 -*-

import pytest
from ckan.cli.cli import ckan
import ckan.cli.db as db

class TestPluginOrder(object):

    @pytest.mark.ckan_config(u"ckan.plugins", u"test_plugin_order_first test_plugin_order_second")
    @pytest.mark.usefixtures(u"with_plugins")
    def test_templates_and_helpers_order_first_second(self, app):
        res = app.get('/')
        assert "Template of First plugin, helper response: First helper" in res.body


    @pytest.mark.ckan_config(u"ckan.plugins", u"test_plugin_order_second test_plugin_order_first ")
    @pytest.mark.usefixtures(u"with_plugins")
    def test_templates_and_helpers_order_second_first(self, app):
        res = app.get('/')
        assert "Template of Second plugin, helper response: Second helper" in res.body

    @pytest.mark.ckan_config("ckan.plugins", "test_plugin_order_first test_plugin_order_third test_plugin_order_second")
    @pytest.mark.usefixtures("with_plugins", "with_extended_cli")
    def test_pending_order(self, cli):

        db._run_migrations(u'test_plugin_order_first', None, False)
        db._run_migrations(u'test_plugin_order_third', None, False)
        db._run_migrations(u'test_plugin_order_second', None, False)

        result = cli.invoke(ckan, ["db", "pending-migrations"])
        assert result.output == ('2 unapplied migrations for test_plugin_order_first\n'
                                 '2 unapplied migrations for test_plugin_order_third\n'
                                 '2 unapplied migrations for test_plugin_order_second\n'
                                 'Upgrading DB: SUCCESS\n')
