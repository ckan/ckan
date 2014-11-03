'''Unit tests for ckan/logic/action/update.py.'''
import datetime

from nose.tools import assert_equals, assert_raises
import mock
import pylons.config as config

#import ckan.logic as logic
from ckan.new_tests import helpers
#import ckan.new_tests.factories as factories

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
            name='somethingnew',
            )

        assert_equals(dataset['name'], 'somethingnew')
        assert_equals(dataset['notes'], 'some test now')

        assert_equals(
            helpers.call_action('package_show', id='somethingnew')['notes'],
            'some test now')
