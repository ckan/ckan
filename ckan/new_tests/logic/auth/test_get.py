'''Unit tests for ckan/logic/auth/get.py.

'''

from nose.tools import assert_raises

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.logic as logic
from ckan import model


class TestGet(object):

    def setup(self):
        helpers.reset_db()

    def test_package_show__deleted_dataset_is_hidden_to_public(self):
        dataset = factories.Dataset(state='deleted')
        context = {'model': model}
        context['user'] = ''

        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'package_show', context=context,
                      id=dataset['name'])

    def test_package_show__deleted_dataset_is_visible_to_editor(self):

        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        org = factories.Organization(users=[fred])
        dataset = factories.Dataset(owner_org=org['id'], state='deleted')
        context = {'model': model}
        context['user'] = 'fred'

        ret = helpers.call_auth('package_show', context=context,
                                id=dataset['name'])
        assert ret

    def test_group_show__deleted_group_is_hidden_to_public(self):
        group = factories.Group(state='deleted')
        context = {'model': model}
        context['user'] = ''

        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'group_show', context=context,
                      id=group['name'])

    def test_group_show__deleted_group_is_visible_to_its_member(self):

        fred = factories.User(name='fred')
        org = factories.Group(users=[fred])
        context = {'model': model}
        context['user'] = 'fred'

        ret = helpers.call_auth('group_show', context=context,
                                id=org['name'])
        assert ret

    def test_group_show__deleted_org_is_visible_to_its_member(self):

        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        org = factories.Organization(users=[fred])
        context = {'model': model}
        context['user'] = 'fred'

        ret = helpers.call_auth('group_show', context=context,
                                id=org['name'])
        assert ret
