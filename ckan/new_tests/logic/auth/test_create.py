'''Unit tests for ckan/logic/auth/create.py.

'''

import mock
import nose

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

logic = helpers.logic


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

        gmc.return_value = {'success': False}
        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'user_invite', context=context, **data_dict)

        gmc.return_value = {'success': True}
        result = helpers.call_auth('user_invite', context=context, **data_dict)
        assert result is True
