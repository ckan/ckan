# encoding: utf-8

'''Unit tests for ckan/logic/auth/get.py.

'''

from nose.tools import assert_raises

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic as logic
from ckan import model


class TestUserListAuth(object):

    @helpers.change_config(u'ckan.auth.public_user_details', u'false')
    def test_auth_user_list(self):
        context = {'user': None,
                   'model': model}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'user_list', context=context)

    def test_authed_user_list(self):
        context = {'user': None,
                   'model': model}
        assert helpers.call_auth('user_list', context=context)

    def test_user_list_email_parameter(self):
        context = {'user': None,
                   'model': model}
        # using the 'email' parameter is not allowed (unless sysadmin)
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'user_list', email='a@example.com', context=context)


class TestUserShowAuth(object):

    def setup(self):
        helpers.reset_db()

    @helpers.change_config(u'ckan.auth.public_user_details', u'false')
    def test_auth_user_show(self):
        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        context = {'user': None,
                   'model': model}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'user_show', context=context, id=fred['id'])

    def test_authed_user_show(self):
        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        context = {'user': None,
                   'model': model}
        assert helpers.call_auth('user_show', context=context, id=fred['id'])


class TestPackageShowAuth(object):

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


class TestGroupShowAuth(object):

    def setup(self):
        helpers.reset_db()

    def test_group_show__deleted_group_is_hidden_to_public(self):
        group = factories.Group(state='deleted')
        context = {'model': model}
        context['user'] = ''

        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'group_show', context=context,
                      id=group['name'])

    def test_group_show__deleted_group_is_visible_to_its_member(self):

        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        org = factories.Group(users=[fred], state='deleted')
        context = {'model': model}
        context['user'] = 'fred'

        ret = helpers.call_auth('group_show', context=context,
                                id=org['name'])
        assert ret

    def test_group_show__deleted_org_is_visible_to_its_member(self):

        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        org = factories.Organization(users=[fred], state='deleted')
        context = {'model': model}
        context['user'] = 'fred'

        ret = helpers.call_auth('group_show', context=context,
                                id=org['name'])
        assert ret

    @helpers.change_config(u'ckan.auth.public_user_details', u'false')
    def test_group_show__user_is_hidden_to_public(self):
        group = factories.Group()
        context = {'model': model}
        context['user'] = ''

        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'group_show', context=context,
                      id=group['name'], include_users=True)

    def test_group_show__user_is_avail_to_public(self):
        group = factories.Group()
        context = {'model': model}
        context['user'] = ''

        assert helpers.call_auth('group_show', context=context,
                                 id=group['name'])


class TestConfigOptionShowAuth(object):

    def setup(self):
        helpers.reset_db()

    def test_config_option_show_anon_user(self):
        '''An anon user is not authorized to use config_option_show action.'''
        context = {'user': None, 'model': None}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'config_option_show', context=context)

    def test_config_option_show_normal_user(self):
        '''A normal logged in user is not authorized to use config_option_show
        action.'''
        factories.User(name='fred')
        context = {'user': 'fred', 'model': None}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'config_option_show', context=context)

    def test_config_option_show_sysadmin(self):
        '''A sysadmin is authorized to use config_option_show action.'''
        factories.Sysadmin(name='fred')
        context = {'user': 'fred', 'model': None}
        assert helpers.call_auth('config_option_show', context=context)


class TestConfigOptionListAuth(object):

    def setup(self):
        helpers.reset_db()

    def test_config_option_list_anon_user(self):
        '''An anon user is not authorized to use config_option_list action.'''
        context = {'user': None, 'model': None}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'config_option_list', context=context)

    def test_config_option_list_normal_user(self):
        '''A normal logged in user is not authorized to use config_option_list
        action.'''
        factories.User(name='fred')
        context = {'user': 'fred', 'model': None}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'config_option_list', context=context)

    def test_config_option_list_sysadmin(self):
        '''A sysadmin is authorized to use config_option_list action.'''
        factories.Sysadmin(name='fred')
        context = {'user': 'fred', 'model': None}
        assert helpers.call_auth('config_option_list', context=context)
