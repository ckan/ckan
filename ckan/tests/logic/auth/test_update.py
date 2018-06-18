# encoding: utf-8

'''Unit tests for ckan/logic/auth/update.py.

'''
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import mock
import nose

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestUpdate(object):

    def test_user_update_visitor_cannot_update_user(self):
        '''Visitors should not be able to update users' accounts.'''

        # Make a mock ckan.model.User object, Fred.
        fred = factories.MockUser(name='fred')

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return Fred.
        mock_model.User.get.return_value = fred

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.
        context = {'model': mock_model}

        # No user is going to be logged-in.
        context['user'] = '127.0.0.1'

        # Make the visitor try to update Fred's user account.
        params = {
            'id': fred.id,
            'name': 'updated_user_name',
        }

        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'user_update', context=context, **params)

    # START-AFTER

    def test_user_update_user_cannot_update_another_user(self):
        '''Users should not be able to update other users' accounts.'''

        # 1. Setup.

        # Make a mock ckan.model.User object, Fred.
        fred = factories.MockUser(name='fred')

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return Fred.
        mock_model.User.get.return_value = fred

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.
        context = {'model': mock_model}

        # The logged-in user is going to be Bob, not Fred.
        context['user'] = 'bob'

        # 2. Call the function that's being tested, once only.

        # Make Bob try to update Fred's user account.
        params = {
            'id': fred.id,
            'name': 'updated_user_name',
        }

        # 3. Make assertions about the return value and/or side-effects.

        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'user_update', context=context, **params)

        # 4. Do nothing else!

    # END-BEFORE

    def test_user_update_user_can_update_herself(self):
        '''Users should be authorized to update their own accounts.'''

        # Make a mock ckan.model.User object, Fred.
        fred = factories.MockUser(name='fred')

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return our mock user.
        mock_model.User.get.return_value = fred

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.
        context = {'model': mock_model}

        # The 'user' in the context has to match fred.name, so that the
        # auth function thinks that the user being updated is the same user as
        # the user who is logged-in.
        context['user'] = fred.name

        # Make Fred try to update his own user name.
        params = {
            'id': fred.id,
            'name': 'updated_user_name',
        }

        result = helpers.call_auth('user_update', context=context, **params)
        assert result is True

    def test_user_update_with_no_user_in_context(self):

        # Make a mock ckan.model.User object.
        mock_user = factories.MockUser(name='fred')

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return our mock user.
        mock_model.User.get.return_value = mock_user

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.
        context = {'model': mock_model}

        # For this test we're going to have no 'user' in the context.
        context['user'] = None

        params = {
            'id': mock_user.id,
            'name': 'updated_user_name',
        }

        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'user_update', context=context, **params)

    def test_user_generate_own_apikey(self):
        fred = factories.MockUser(name='fred')
        mock_model = mock.MagicMock()
        mock_model.User.get.return_value = fred
        # auth_user_obj shows user as logged in for non-anonymous auth
        # functions
        context = {'model': mock_model, 'auth_user_obj': fred}
        context['user'] = fred.name
        params = {
            'id': fred.id,
        }

        result = helpers.call_auth('user_generate_apikey', context=context,
                                   **params)
        assert result is True

    def test_user_generate_apikey_without_logged_in_user(self):
        fred = factories.MockUser(name='fred')
        mock_model = mock.MagicMock()
        mock_model.User.get.return_value = fred
        context = {'model': mock_model}
        context['user'] = None
        params = {
            'id': fred.id,
        }

        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'user_generate_apikey', context=context,
                                 **params)

    def test_user_generate_apikey_for_another_user(self):
        fred = factories.MockUser(name='fred')
        bob = factories.MockUser(name='bob')
        mock_model = mock.MagicMock()
        mock_model.User.get.return_value = fred
        # auth_user_obj shows user as logged in for non-anonymous auth
        # functions
        context = {'model': mock_model, 'auth_user_obj': bob}
        context['user'] = bob.name
        params = {
            'id': fred.id,
        }

        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'user_generate_apikey', context=context,
                                 **params)


class TestUpdateResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def test_anon_can_not_update(self):

        resource_view = factories.ResourceView()

        params = {'id': resource_view['id'],
                  'title': 'Resource View Updated',
                  'view_type': 'image_view',
                  'image_url': 'url'}

        context = {'user': None, 'model': model}
        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_view_update', context=context,
                                 **params)

    def test_authorized_if_user_has_permissions_on_dataset(self):

        user = factories.User()

        dataset = factories.Dataset(user=user)

        resource = factories.Resource(user=user, package_id=dataset['id'])

        resource_view = factories.ResourceView(resource_id=resource['id'])

        params = {'id': resource_view['id'],
                  'resource_id': resource['id'],
                  'title': 'Resource View Updated',
                  'view_type': 'image_view',
                  'image_url': 'url'}

        context = {'user': user['name'], 'model': model}
        response = helpers.call_auth('resource_view_update', context=context,
                                     **params)

        assert_equals(response, True)

    def test_not_authorized_if_user_has_no_permissions_on_dataset(self):

        org = factories.Organization()

        user = factories.User()

        member = {'username': user['name'],
                  'role': 'admin',
                  'id': org['id']}
        helpers.call_action('organization_member_create', **member)

        user_2 = factories.User()

        dataset = factories.Dataset(owner_org=org['id'])

        resource = factories.Resource(package_id=dataset['id'])

        resource_view = factories.ResourceView(resource_id=resource['id'])

        params = {'id': resource_view['id'],
                  'resource_id': resource['id'],
                  'title': 'Resource View Updated',
                  'view_type': 'image_view',
                  'image_url': 'url'}

        context = {'user': user_2['name'], 'model': model}
        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_view_update', context=context,
                                 **params)


class TestConfigOptionUpdateAuth(object):

    def setup(self):
        helpers.reset_db()

    def test_config_option_update_anon_user(self):
        '''An anon user is not authorized to use config_option_update
        action.'''
        context = {'user': None, 'model': None}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'config_option_update', context=context)

    def test_config_option_update_normal_user(self):
        '''A normal logged in user is not authorized to use config_option_update
        action.'''
        factories.User(name='fred')
        context = {'user': 'fred', 'model': None}
        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'config_option_update', context=context)

    def test_config_option_update_sysadmin(self):
        '''A sysadmin is authorized to use config_option_update action.'''
        factories.Sysadmin(name='fred')
        context = {'user': 'fred', 'model': None}
        assert helpers.call_auth('config_option_update', context=context)
