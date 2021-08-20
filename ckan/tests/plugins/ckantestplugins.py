# encoding: utf-8

from collections import defaultdict

import ckan.plugins as p
import ckan.tests.plugins.mock_plugin as mock_plugin


class MapperPlugin(p.SingletonPlugin):
    p.implements(p.IMapper, inherit=True)

    def __init__(self, *args, **kw):
        self.calls = []

    def _get_instance_name(self, instance):
        return getattr(instance, "name", None)

    def before_insert(self, mapper, conn, instance):
        self.calls.append(("before_insert", self._get_instance_name(instance)))

    def after_insert(self, mapper, conn, instance):
        self.calls.append(("after_insert", self._get_instance_name(instance)))

    def before_delete(self, mapper, conn, instance):
        self.calls.append(("before_delete", self._get_instance_name(instance)))

    def after_delete(self, mapper, conn, instance):
        self.calls.append(("after_delete", self._get_instance_name(instance)))


class MapperPlugin2(MapperPlugin):
    p.implements(p.IMapper)


class SessionPlugin(p.SingletonPlugin):
    p.implements(p.ISession, inherit=True)

    def __init__(self, *args, **kw):
        self.added = []
        self.deleted = []

    def before_insert(self, mapper, conn, instance):
        self.added.append(instance)

    def before_delete(self, mapper, conn, instance):
        self.deleted.append(instance)


class RoutesPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    def __init__(self, *args, **kw):
        self.calls_made = []

    def before_map(self, map):
        self.calls_made.append("before_map")
        return map

    def after_map(self, map):
        self.calls_made.append("after_map")
        return map


class PluginObserverPlugin(mock_plugin.MockSingletonPlugin):
    p.implements(p.IPluginObserver)


class ActionPlugin(p.SingletonPlugin):
    p.implements(p.IActions)

    def get_actions(self):
        return {"status_show": lambda context, data_dict: {}}


class AuthPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)

    def get_auth_functions(self):
        return {"package_list": lambda context, data_dict: {}}


class MockGroupControllerPlugin(p.SingletonPlugin):
    p.implements(p.IGroupController)

    def __init__(self, *args, **kw):
        self.calls = defaultdict(int)

    def read(self, entity):
        self.calls["read"] += 1

    def create(self, entity):
        self.calls["create"] += 1

    def edit(self, entity):
        self.calls["edit"] += 1

    def delete(self, entity):
        self.calls["delete"] += 1

    def before_view(self, data_dict):
        self.calls["before_view"] += 1
        return data_dict


class MockPackageControllerPlugin(p.SingletonPlugin):
    p.implements(p.IPackageController)

    def __init__(self, *args, **kw):
        self.calls = defaultdict(int)

    def read(self, entity):
        self.calls["read"] += 1

    def create(self, entity):
        self.calls["create"] += 1

    def edit(self, entity):
        self.calls["edit"] += 1

    def delete(self, entity):
        self.calls["delete"] += 1

    def before_search(self, search_params):
        self.calls["before_search"] += 1
        return search_params

    def after_search(self, search_results, search_params):
        self.calls["after_search"] += 1
        return search_results

    def before_index(self, data_dict):
        self.calls["before_index"] += 1
        return data_dict

    def before_view(self, data_dict):
        self.calls["before_view"] += 1
        return data_dict

    def after_create(self, context, data_dict):
        self.calls["after_create"] += 1
        self.id_in_dict = "id" in data_dict

        return data_dict

    def after_update(self, context, data_dict):
        self.calls["after_update"] += 1
        return data_dict

    def after_delete(self, context, data_dict):
        self.calls["after_delete"] += 1
        return data_dict

    def after_show(self, context, data_dict):
        self.calls["after_show"] += 1
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles


class MockResourcePreviewExtension(mock_plugin.MockSingletonPlugin):
    p.implements(p.IResourcePreview)

    def __init__(self, *args, **kw):
        self.calls = defaultdict(int)

    def setup_template_variables(self, context, data_dict):
        self.calls["setup_template_variables"] += 1

    def can_preview(self, data_dict):
        assert isinstance(data_dict["resource"], dict)
        assert isinstance(data_dict["package"], dict)
        assert "on_same_domain" in data_dict["resource"]

        self.calls["can_preview"] += 1
        return data_dict["resource"]["format"].lower() == "mock"

    def preview_template(self, context, data_dict):
        assert isinstance(data_dict["resource"], dict)
        assert isinstance(data_dict["package"], dict)

        self.calls["preview_templates"] += 1
        return "tests/mock_resource_preview_template.html"


class JsonMockResourcePreviewExtension(mock_plugin.MockSingletonPlugin):
    p.implements(p.IResourcePreview)

    def __init__(self, *args, **kw):
        self.calls = defaultdict(int)

    def setup_template_variables(self, context, data_dict):
        self.calls["setup_template_variables"] += 1

    def can_preview(self, data_dict):
        self.calls["can_preview"] += 1
        return data_dict["resource"]["format"].lower() == "json"

    def preview_template(self, context, data_dict):
        self.calls["preview_templates"] += 1
        return "tests/mock_json_resource_preview_template.html"
