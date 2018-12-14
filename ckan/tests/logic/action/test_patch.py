# encoding: utf-8

'''Unit tests for ckan/logic/action/patch.py.'''
import datetime

from nose.tools import assert_equals, assert_raises
import mock
from ckan.common import config

from ckan.tests import helpers, factories


class TestPatch(helpers.FunctionalTestBase):

    def test_package_patch_updating_single_field(self):
        user = factories.User()
        dataset = factories.Dataset(
            name='annakarenina',
            notes='some test now',
            user=user)

        dataset = helpers.call_action(
            'package_patch',
            id=dataset['id'],
            name='somethingnew')

        assert_equals(dataset['name'], 'somethingnew')
        assert_equals(dataset['notes'], 'some test now')

        dataset2 = helpers.call_action('package_show', id=dataset['id'])

        assert_equals(dataset2['name'], 'somethingnew')
        assert_equals(dataset2['notes'], 'some test now')

    def test_resource_patch_updating_single_field(self):
        user = factories.User()
        dataset = factories.Dataset(
            name='annakarenina',
            notes='some test now',
            user=user,
            resources=[{'url': 'http://example.com/resource'}])

        resource = helpers.call_action(
            'resource_patch',
            id=dataset['resources'][0]['id'],
            name='somethingnew')

        assert_equals(resource['name'], 'somethingnew')
        assert_equals(resource['url'], 'http://example.com/resource')

        dataset2 = helpers.call_action('package_show', id=dataset['id'])

        resource2 = dataset2['resources'][0]
        assert_equals(resource2['name'], 'somethingnew')
        assert_equals(resource2['url'], 'http://example.com/resource')

    def test_group_patch_updating_single_field(self):
        user = factories.User()
        group = factories.Group(
            name='economy',
            description='some test now',
            user=user)

        group = helpers.call_action(
            'group_patch',
            id=group['id'],
            description='somethingnew',
            context={'user': user['name']})

        assert_equals(group['name'], 'economy')
        assert_equals(group['description'], 'somethingnew')

        group2 = helpers.call_action('group_show', id=group['id'])

        assert_equals(group2['name'], 'economy')
        assert_equals(group2['description'], 'somethingnew')

    def test_group_patch_preserve_datasets(self):
        user = factories.User()
        group = factories.Group(
            name='economy',
            description='some test now',
            user=user)
        factories.Dataset(groups=[{'name': group['name']}])

        group2 = helpers.call_action('group_show', id=group['id'])
        assert_equals(1, group2['package_count'])

        group = helpers.call_action(
            'group_patch',
            id=group['id'],
            context={'user': user['name']})

        group3 = helpers.call_action('group_show', id=group['id'])
        assert_equals(1, group3['package_count'])

        group = helpers.call_action(
            'group_patch',
            id=group['id'],
            packages=[],
            context={'user': user['name']})

        group4 = helpers.call_action(
            'group_show', id=group['id'], include_datasets=True
        )
        assert_equals(0, group4['package_count'])

    def test_organization_patch_updating_single_field(self):
        user = factories.User()
        organization = factories.Organization(
            name='economy',
            description='some test now',
            user=user)

        organization = helpers.call_action(
            'organization_patch',
            id=organization['id'],
            description='somethingnew',
            context={'user': user['name']})

        assert_equals(organization['name'], 'economy')
        assert_equals(organization['description'], 'somethingnew')

        organization2 = helpers.call_action(
            'organization_show',
            id=organization['id'])

        assert_equals(organization2['name'], 'economy')
        assert_equals(organization2['description'], 'somethingnew')
