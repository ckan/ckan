'''Unit tests for ckan/logic/action/patch.py.'''
import datetime

from nose.tools import assert_equals, assert_raises
import mock
import pylons.config as config

from ckan.new_tests import helpers, factories


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
