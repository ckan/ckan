# encoding: utf-8

import pytest

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", u"example_idatasetform")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestPackageController(object):

    def test_edit_converted_extra_field(self, app, ckan_config):
        dataset = factories.Dataset(custom_text="foo")
        dataset.update(custom_text='bar')
        resp = helpers.call_action('package_update', **dataset)
        assert resp["custom_text"] == u"bar"
