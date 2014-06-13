'''Unit tests for ckan/logic/auth/create.py.

'''

import mock
import nose

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.logic.auth.create as auth_create

logic = helpers.logic
assert_equals = nose.tools.assert_equals


class TestCreateDatasetSettings(object):
    def test_anon_cant_create_dataset(self):
        response = auth_create.package_create({'user': None}, None)
        assert_equals(response['success'], False)

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    def test_anon_can_create_dataset(self):
        response = auth_create.package_create({'user': None}, None)
        assert_equals(response['success'], True)

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    @helpers.change_config('ckan.auth.create_dataset_if_not_in_organization',
                           False)
    def test_cdnio_overrides_acd(self):
        response = auth_create.package_create({'user': None}, None)
        assert_equals(response['success'], False)

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    @helpers.change_config('ckan.auth.create_unowned_dataset', False)
    def test_cud_overrides_acd(self):
        response = auth_create.package_create({'user': None}, None)
        assert_equals(response['success'], False)


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
