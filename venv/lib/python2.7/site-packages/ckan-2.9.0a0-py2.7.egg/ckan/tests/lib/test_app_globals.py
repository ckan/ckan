# encoding: utf-8

from ckan.lib.app_globals import app_globals as g


class TestGlobals(object):
    def test_config_not_set(self):
        # ckan.site_about has not been configured.
        # Behaviour has always been to return an empty string.
        assert g.site_about == ''

    def test_config_set_to_blank(self):
        # ckan.site_description is configured but with no value.
        # Behaviour has always been to return an empty string.
        assert g.site_description == ''

    def test_set_from_ini(self):
        # ckan.template_head_end is configured in test-core.ini
        assert g.template_head_end == '<link rel="stylesheet" href="TEST_TEMPLATE_HEAD_END.css" type="text/css">'
