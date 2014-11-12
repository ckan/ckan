'''Unit tests for ckan/logic/auth/create.py.

'''

import mock
import nose

import ckan.model as core_model
import ckan.plugins as p

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.logic.auth.create as auth_create

logic = helpers.logic
assert_equals = nose.tools.assert_equals


class TestCreateDatasetAnonymousSettings(object):
    def test_anon_cant_create(self):
        response = auth_create.package_create({'user': None}, None)
        assert_equals(response['success'], False)

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    def test_anon_can_create(self):
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


class TestCreateDatasetLoggedInSettings(object):
    def setup(self):
        helpers.reset_db()

    def test_no_org_user_can_create(self):
        user = factories.User()
        response = auth_create.package_create({'user': user['name']}, None)
        assert_equals(response['success'], True)

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    @helpers.change_config('ckan.auth.create_dataset_if_not_in_organization',
                           False)
    def test_no_org_user_cant_create_if_cdnio_false(self):
        user = factories.User()
        response = auth_create.package_create({'user': user['name']}, None)
        assert_equals(response['success'], False)

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    @helpers.change_config('ckan.auth.create_unowned_dataset', False)
    def test_no_org_user_cant_create_if_cud_false(self):
        user = factories.User()
        response = auth_create.package_create({'user': user['name']}, None)
        assert_equals(response['success'], False)

    def test_same_org_user_can_create(self):
        user = factories.User()
        org_users = [{'name': user['name'], 'capacity': 'editor'}]
        org = factories.Organization(users=org_users)
        dataset = {'name': 'same-org-user-can-create', 'owner_org': org['id']}
        context = {'user': user['name'], 'model': core_model}
        response = auth_create.package_create(context, dataset)
        assert_equals(response['success'], True)

    def test_different_org_user_cant_create(self):
        user = factories.User()
        org_users = [{'name': user['name'], 'capacity': 'editor'}]
        org1 = factories.Organization(users=org_users)
        org2 = factories.Organization()
        dataset = {'name': 'different-org-user-cant-create',
                   'owner_org': org2['id']}
        context = {'user': user['name'], 'model': core_model}
        response = auth_create.package_create(context, dataset)
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


class TestCreateResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def test_authorized_if_user_has_permissions_on_dataset(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        resource = factories.Resource(user=user, package_id=dataset['id'])

        resource_view = {'resource_id': resource['id'],
                         'title': u'Resource View',
                         'view_type': u'image',
                         'image_url': 'url'}

        context = {'user': user['name'], 'model': core_model}
        response = helpers.call_auth('resource_view_create',
                                     context=context, **resource_view)
        assert_equals(response, True)

#    TODO: enable once #2037 is merged
#    def test_not_authorized_if_user_has_no_permissions_on_dataset(self):
#
#        org = factories.Organization()
#
#        user = factories.User()
#
#        member = {'username': user['name'],
#                  'role': 'admin',
#                  'id': org['id']}
#        helpers.call_action('organization_member_create', **member)
#
#        user_2 = factories.User()
#
#        dataset = factories.Dataset(owner_org=org['id'])
#
#        resource = factories.Resource(package_id=dataset['id'])
#
#        resource_view = {'resource_id': resource['id'],
#                         'title': u'Resource View',
#                         'view_type': u'image',
#                         'image_url': 'url'}
#
#        context = {'user': user_2['name'], 'model': core_model}
#        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
#                                 'resource_view_create', context=context,
#                                 **resource_view)

    def test_not_authorized_if_not_logged_in(self):

        resource_view = {'title': u'Resource View',
                         'view_type': u'image',
                         'image_url': 'url'}

        context = {'user': None, 'model': core_model}
        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_view_create', context=context,
                                 **resource_view)
