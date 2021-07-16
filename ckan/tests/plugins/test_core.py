# encoding: utf-8

import pytest

import ckan.plugins as p


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config(
    "ckan.plugins",
    "example_idatasetform_v1 example_idatasetform_v2 example_idatasetform_v3")
def test_plugins_order_in_pluginimplementations():

    assert (
        [plugin.name for plugin in p.PluginImplementations(p.IDatasetForm)] ==
        [
            "example_idatasetform_v1",
            "example_idatasetform_v2",
            "example_idatasetform_v3"
        ]
    )


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config(
    "ckan.plugins",
    "example_idatasetform_v1 example_idatasetform_v3 example_idatasetform_v2")
def test_plugins_order_in_pluginimplementations_matches_config():

    assert (
        [plugin.name for plugin in p.PluginImplementations(p.IDatasetForm)] ==
        [
            "example_idatasetform_v1",
            "example_idatasetform_v3",
            "example_idatasetform_v2"
        ]
    )
