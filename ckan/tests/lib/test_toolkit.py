import ckan.tests.helpers as helpers

from nose.tools import assert_equals, assert_not_equals
import ckan.plugins.toolkit as t
from pylons import config
from pylons import translator


class TestToolkit(helpers.FunctionalTestBase):

    def test_config_is_in_toolkit(self):
        assert sorted(t.config.keys()) == sorted(config.keys())

    def test_config_values_are_accurate(self):
        for k, v in t.config.iteritems():
            assert config[k] == v

    def test_translator(self):
        assert translator.gettext("Test") == \
            t.translator.gettext("Test")
