# encoding: utf-8

import pytest

import ckan.plugins as p


@pytest.mark.usefixtures(u"with_plugins")
@pytest.mark.ckan_config(
    u"ckan.plugins",
    u"example_idatasetform_v1 example_idatasetform_v2 example_idatasetform_v3")
def test_plugins_order_in_pluginimplementations():

    assert (
        [plugin.name for plugin in p.PluginImplementations(p.IDatasetForm)] ==
        [
            u"example_idatasetform_v1",
            u"example_idatasetform_v2",
            u"example_idatasetform_v3"
        ]
    )
