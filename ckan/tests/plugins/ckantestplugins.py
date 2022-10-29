# encoding: utf-8

from collections import defaultdict

import ckan.plugins as p
import ckan.tests.plugins.mock_plugin as mock_plugin


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
        super().__init__(*args, **kw)
        self.calls = defaultdict(int)

    def read(self, entity):
        self.calls["read"] += 1

    def create(self, entity):
        self.calls["create"] += 1

    def edit(self, entity):
        self.calls["edit"] += 1

    def delete(self, entity):
        self.calls["delete"] += 1

    # this method deliberately uses deprecated `before_search` name instead of
    # `before_dataset_search`. Change the name after support for deprecated
    # names is dropped.
    def before_search(self, search_params):
        self.calls["before_dataset_search"] += 1
        return search_params

    def after_dataset_search(self, search_results, search_params):
        self.calls["after_dataset_search"] += 1
        return search_results

    def before_dataset_index(self, data_dict):
        self.calls["before_dataset_index"] += 1
        return data_dict

    def before_dataset_view(self, data_dict):
        self.calls["before_dataset_view"] += 1
        return data_dict

    def after_dataset_create(self, context, data_dict):
        self.calls["after_dataset_create"] += 1
        self.id_in_dict = "id" in data_dict

        return data_dict

    def after_dataset_update(self, context, data_dict):
        self.calls["after_dataset_update"] += 1
        return data_dict

    def after_dataset_delete(self, context, data_dict):
        self.calls["after_dataset_delete"] += 1
        return data_dict

    def after_dataset_show(self, context, data_dict):
        self.calls["after_dataset_show"] += 1
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles


class MockResourceViewExtension(mock_plugin.MockSingletonPlugin):
    p.implements(p.IResourceView)

    def __init__(self, *args, **kw):
        self.calls = defaultdict(int)

    def info(self):
        return {
            'name': 'test_resource_view',
            'title': 'Test',
            'default_title': 'Test',
        }

    def setup_template_variables(self, context, data_dict):
        self.calls["setup_template_variables"] += 1

    def can_view(self, data_dict):
        assert isinstance(data_dict["resource"], dict)
        assert isinstance(data_dict["package"], dict)
        self.calls["can_view"] += 1
        return data_dict["resource"]["format"].lower() == "mock"

    def view_template(self, context, data_dict):
        assert isinstance(data_dict["resource"], dict)
        assert isinstance(data_dict["package"], dict)

        self.calls["view_template"] += 1
        return "tests/mock_resource_preview_template.html"
