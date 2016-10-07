# encoding: utf-8

import nose.tools

import ckan.model as model
import ckan.plugins as p

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_not_equals = nose.tools.assert_not_equals
ResourceView = model.ResourceView


class TestResourceView(object):
    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')
        if not p.plugin_loaded('webpage_view'):
            p.load('webpage_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')
        p.unload('webpage_view')

    def setup(self):
        model.repo.rebuild_db()

    def test_resource_view_get(self):
        resource_view_id = factories.ResourceView()['id']
        resource_view = ResourceView.get(resource_view_id)

        assert_not_equals(resource_view, None)

    def test_get_count_view_type(self):
        factories.ResourceView(view_type='image_view')
        factories.ResourceView(view_type='webpage_view')

        result = ResourceView.get_count_not_in_view_types(['image_view'])

        assert_equals(result, [('webpage_view', 1)])

    def test_delete_view_type(self):
        factories.ResourceView(view_type='image_view')
        factories.ResourceView(view_type='webpage_view')

        ResourceView.delete_not_in_view_types(['image_view'])

        result = ResourceView.get_count_not_in_view_types(['image_view'])
        assert_equals(result, [])

    def test_delete_view_type_doesnt_commit(self):
        factories.ResourceView(view_type='image_view')
        factories.ResourceView(view_type='webpage_view')

        ResourceView.delete_not_in_view_types(['image_view'])
        model.Session.rollback()

        result = ResourceView.get_count_not_in_view_types(['image_view'])
        assert_equals(result, [('webpage_view', 1)])

    def test_purging_resource_removes_its_resource_views(self):
        resource_view_dict = factories.ResourceView()
        resource = model.Resource.get(resource_view_dict['resource_id'])

        resource.purge()
        model.repo.commit_and_remove()

        assert_equals(ResourceView.get(resource_view_dict['id']), None)
