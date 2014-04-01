'''Unit tests for ckan/logic/auth/create.py.

'''

import mock
import nose

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


class TestCreate(object):

    def setup(self):
        helpers.reset_db()

    @mock.patch('ckan.logic.auth.create.group_member_create')
    def test_user_invite_delegates_correctly_to_group_member_create(self, gmc):
        user = factories.User()
        context = {
            'user': user['name'],
            'model': None,
            'auth_user_obj': user
        }
        data_dict = {'group_id': 42}
        group_member_create_data_dict = data_dict.copy()
        group_member_create_data_dict['id'] = data_dict['group_id']

        with nose.tools.assert_raises(helpers.logic.NotAuthorized):
            gmc.return_value = {'success': False}
            helpers.call_auth('user_invite', context=context, **data_dict)

        gmc.return_value = {'success': True}
        assert helpers.call_auth('user_invite', context=context, **data_dict)

        gmc.assert_called_twice_with(context, group_member_create_data_dict)
