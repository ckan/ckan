# encoding: utf-8

import nose.tools

import ckan.model as model
import ckan.plugins as p

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_not_equals = nose.tools.assert_not_equals
Resource = model.Resource


class TestResource(object):
    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def setup(self):
        model.repo.rebuild_db()

    def test_edit_url(self):
        res_dict = factories.Resource(url='http://first')
        res = Resource.get(res_dict['id'])
        res.url = 'http://second'
        model.repo.new_revision()
        model.repo.commit_and_remove()
        res = Resource.get(res_dict['id'])
        assert_equals(res.url, 'http://second')

    def test_edit_extra(self):
        res_dict = factories.Resource(newfield='first')
        res = Resource.get(res_dict['id'])
        res.extras = {'newfield': 'second'}
        res.url
        model.repo.new_revision()
        model.repo.commit_and_remove()
        res = Resource.get(res_dict['id'])
        assert_equals(res.extras['newfield'], 'second')

    def test_get_all_without_views_returns_all_resources_without_views(self):
        # Create resource with resource_view
        factories.ResourceView()

        expected_resources = [
            factories.Resource(format='format'),
            factories.Resource(format='other_format')
        ]

        resources = Resource.get_all_without_views()

        expected_resources_ids = [r['id'] for r in expected_resources]
        resources_ids = [r.id for r in resources]

        assert_equals(expected_resources_ids.sort(), resources_ids.sort())

    def test_get_all_without_views_accepts_list_of_formats_ignoring_case(self):
        factories.Resource(format='other_format')
        resource_id = factories.Resource(format='format')['id']

        resources = Resource.get_all_without_views(['FORMAT'])

        length = len(resources)
        assert length == 1, 'Expected 1 resource, but got %d' % length
        assert_equals([resources[0].id], [resource_id])

    def test_resource_count(self):
        '''Resource.count() should return a count of instances of Resource
        class'''
        assert_equals(Resource.count(), 0)
        factories.Resource()
        factories.Resource()
        factories.Resource()
        assert_equals(Resource.count(), 3)
