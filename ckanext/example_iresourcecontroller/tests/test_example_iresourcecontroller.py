# encoding: utf-8

"""Tests for the ckanext.example_iauthfunctions extension.

"""
import pytest

import ckan.plugins
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config("ckan.plugins", "example_iresourcecontroller")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestExampleIResourceController(object):
    """Tests for the plugin that uses IResourceController.

    """

    def test_resource_controller_plugin_create(self):
        user = factories.Sysadmin()
        package = factories.Dataset(user=user)

        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_create",
            package_id=package["id"],
            name="test-resource",
            url="http://resource.create/",
            apikey=user["apikey"],
        )

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 0, plugin.counter
        assert plugin.counter["after_resource_update"] == 0, plugin.counter
        assert plugin.counter["before_resource_delete"] == 0, plugin.counter
        assert plugin.counter["after_resource_delete"] == 0, plugin.counter

    def test_resource_controller_plugin_update_stale_search_cache(self, monkeypatch):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user, url="http://resource.initial/")
        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        import ckan.lib.search as search
        import json
        # Simulate Solr returning the pre-update dataset cache
        orig_show = search.show
        def mock_search_show(name_or_id):
            res = orig_show(name_or_id)
            for k in ['data_dict', 'validated_data_dict']:
                if k in res:
                    data = json.loads(res[k])
                    for r in data['resources']:
                        if r['id'] == resource['id']:
                            r['url'] = "http://resource.initial/"
                    res[k] = json.dumps(data)
            return res

        monkeypatch.setattr(search, "show", mock_search_show)

        helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://resource.updated/",
            apikey=user["apikey"],
        )

        assert plugin.last_diagnostics['same_session_res']['url'] == "http://resource.updated/"

    def test_resource_controller_plugin_update_defer_commit(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user, url="http://resource.initial/")
        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        context = {
            "user": user["name"],
            "defer_commit": True,
        }

        helpers.call_action(
            "resource_update",
            context=context,
            id=resource["id"],
            url="http://resource.updated/",
        )

        assert plugin.last_diagnostics['same_session_res']['url'] == "http://resource.updated/"
        # Since commit was deferred, another DB connection cannot see changes yet
        assert plugin.last_diagnostics['fresh_session_db_url'] == "http://resource.initial/"

        # Once the outer transaction commits:
        import ckan.model as model
        model.repo.commit()
        fresh_session = model.meta.create_local_session()
        try:
            fresh_db_res = fresh_session.get(model.Resource, resource['id'])
            assert fresh_db_res.url == "http://resource.updated/"
        finally:
            fresh_session.close()

    def test_resource_controller_plugin_update_with_schema(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user, format="CSV", schema="old_schema", my_extra="old_extra")
        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://resource.updated/",
            format="CSV",
            schema="new_schema",
            my_extra="new_extra",
            apikey=user["apikey"],
        )

        assert plugin.last_diagnostics['hook_resource_schema'] == "new_schema"
        assert plugin.last_diagnostics['same_session_schema'] == "new_schema"
        assert plugin.last_diagnostics['fresh_session_extra'] == "new_extra"

    def test_resource_controller_plugin_update_solr_no_commit(self, monkeypatch):
        import ckan.common as common
        monkeypatch.setitem(common.config, "ckan.search.solr_commit", False)

        user = factories.Sysadmin()
        resource = factories.Resource(user=user)
        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://resource.updated/",
            apikey=user["apikey"],
        )

        assert plugin.last_diagnostics['same_session_res']['url'] == "http://resource.updated/"

    def test_resource_controller_plugin_update(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)
        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://resource.updated/",
            apikey=user["apikey"],
        )

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 1, plugin.counter
        assert plugin.counter["after_resource_update"] == 1, plugin.counter
        assert plugin.counter["before_resource_delete"] == 0, plugin.counter
        assert plugin.counter["after_resource_delete"] == 0, plugin.counter

        # Same-session read: resource_show using context inside hook
        assert plugin.last_diagnostics['same_session_res']['url'] == "http://resource.updated/"

        # Fresh-connection DB read: separate session directly reading Resource table
        assert plugin.last_diagnostics['fresh_session_db_url'] == "http://resource.updated/"

    def test_resource_controller_plugin_patch(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)
        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_patch",
            id=resource["id"],
            url="http://resource.patched/",
            apikey=user["apikey"],
        )

        assert plugin.last_diagnostics['same_session_res']['url'] == "http://resource.patched/"
        assert plugin.last_diagnostics['fresh_session_db_url'] == "http://resource.patched/"

    def test_resource_controller_plugin_delete(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)

        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action(
            "resource_delete", id=resource["id"], apikey=user["apikey"]
        )

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 0, plugin.counter
        assert plugin.counter["after_resource_update"] == 0, plugin.counter
        assert plugin.counter["before_resource_delete"] == 1, plugin.counter
        assert plugin.counter["after_resource_delete"] == 1, plugin.counter

    def test_resource_controller_plugin_show(self):
        """
        Before show gets called by the other methods but we test it
        separately here and make sure that it doesn't call the other
        methods.
        """
        user = factories.Sysadmin()
        package = factories.Dataset(user=user)
        factories.Resource(user=user, package_id=package["id"])

        plugin = ckan.plugins.get_plugin("example_iresourcecontroller")

        helpers.call_action("package_show", name_or_id=package["id"])

        assert plugin.counter["before_resource_create"] == 1, plugin.counter
        assert plugin.counter["after_resource_create"] == 1, plugin.counter
        assert plugin.counter["before_resource_update"] == 0, plugin.counter
        assert plugin.counter["after_resource_update"] == 0, plugin.counter
        assert plugin.counter["before_resource_delete"] == 0, plugin.counter
        assert plugin.counter["after_resource_delete"] == 0, plugin.counter
        assert plugin.counter["before_resource_show"] == 2, plugin.counter
