# encoding: utf-8

'''
Tests for the ckanext.example_ipermissionlabels extension
'''
from nose.tools import assert_raises, assert_equal

import ckan.plugins
from ckan.plugins.toolkit import get_action, NotAuthorized
from ckan.tests.helpers import FunctionalTestBase, call_action, call_auth
from ckan.tests import factories

class TestExampleIPermissionLabels(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        ckan.plugins.load('example_ipermissionlabels')

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('example_ipermissionlabels')

    def test_normal_dataset_permissions_are_normal(self):
        user = factories.User()
        user2 = factories.User()
        user3 = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(user=user2)
        call_action(
            'organization_member_create', None, username=user3['id'],
            id=org2['id'], role='member')

        dataset = factories.Dataset(
            name='d1', user=user, private=True, owner_org=org['id'])
        dataset2 = factories.Dataset(
            name='d2', user=user2, private=True, owner_org=org2['id'])

        results = get_action('package_search')(
            {'user': user['id']}, {})['results']
        names = [r['name'] for r in results]
        assert_equal(names, ['d1'])

        results = get_action('package_search')(
            {'user': user3['id']}, {})['results']
        names = [r['name'] for r in results]
        assert_equal(names, ['d2'])

    def test_proposed_overrides_public(self):
        user = factories.User()
        dataset = factories.Dataset(
            name='d1', notes='Proposed:', user=user)

        results = get_action('package_search')({}, {})['results']
        names = [r['name'] for r in results]
        assert_equal(names, [])

        assert_raises(NotAuthorized, call_auth,
            'package_show', {'user':'', 'model': model}, id='d1')

    def test_proposed_dataset_visible_to_creator(self):
        user = factories.User()
        dataset = factories.Dataset(
            name='d1', notes='Proposed:', user=user)

        results = get_action('package_search')(
            {'user': user['id']}, {})['results']
        names = [r['name'] for r in results]
        assert_equal(names, ['d1'])

        ret = call_auth('package_show',
            {'user': user['id'], 'model': model}, id='d1')
        assert ret['success'], ret

    def test_proposed_dataset_visible_to_org_admin(self):
        user = factories.User()
        user2 = factories.User()
        org = factories.Organization(user=user2)
        dataset = factories.Dataset(
            name='d1', notes='Proposed:', user=user, owner_org=org['id'])

        results = get_action('package_search')(
            {'user': user2['id']}, {})['results']
        names = [r['name'] for r in results]
        assert_equal(names, ['d1'])

        ret = call_auth('package_show',
            {'user': user2['id'], 'model': model}, id='d1')
        assert ret['success'], ret
