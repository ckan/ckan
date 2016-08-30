# encoding: utf-8

import nose.tools

import ckan.plugins as p
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_not_equals = nose.tools.assert_not_equals


class TestFactories(object):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def test_user_factory(self):
        user1 = factories.User()
        user2 = factories.User()
        assert_not_equals(user1['id'], user2['id'])

    def test_resource_factory(self):
        resource1 = factories.Resource()
        resource2 = factories.Resource()
        assert_not_equals(resource1['id'], resource2['id'])

    def test_resource_view_factory(self):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        resource_view1 = factories.ResourceView()
        resource_view2 = factories.ResourceView()
        assert_not_equals(resource_view1['id'], resource_view2['id'])

        p.unload('image_view')

    def test_sysadmin_factory(self):
        sysadmin1 = factories.Sysadmin()
        sysadmin2 = factories.Sysadmin()
        assert_not_equals(sysadmin1['id'], sysadmin2['id'])

    def test_group_factory(self):
        group1 = factories.Group()
        group2 = factories.Group()
        assert_not_equals(group1['id'], group2['id'])

    def test_organization_factory(self):
        organization1 = factories.Organization()
        organization2 = factories.Organization()
        assert_not_equals(organization1['id'], organization2['id'])

    def test_dataset_factory(self):
        dataset1 = factories.Dataset()
        dataset2 = factories.Dataset()
        assert_not_equals(dataset1['id'], dataset2['id'])

    def test_dataset_factory_allows_creation_by_anonymous_user(self):
        dataset = factories.Dataset(user=None)
        assert_equals(dataset['creator_user_id'], None)

    def test_mockuser_factory(self):
        mockuser1 = factories.MockUser()
        mockuser2 = factories.MockUser()
        assert_not_equals(mockuser1['id'], mockuser2['id'])
