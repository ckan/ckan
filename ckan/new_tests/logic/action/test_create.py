'''Unit tests for ckan/logic/auth/create.py.

'''

import mock
import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.model
import ckan.logic

assert_equals = nose.tools.assert_equals


class TestUserInvite(object):

    def setup(self):
        helpers.reset_db()

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_user_invite(self, _):
        invited_user = self._invite_user_to_group()

        assert invited_user is not None
        assert invited_user.is_pending()

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_user_invite_creates_user_with_valid_username(self, _):
        email = 'user$%+abc@email.com'
        invited_user = self._invite_user_to_group(email)

        assert invited_user.name.startswith('user---abc'), invited_user

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_user_invite_assigns_user_to_group_in_expected_role(self, _):
        role = 'admin'
        invited_user = self._invite_user_to_group(role=role)

        group_ids = invited_user.get_group_ids(capacity=role)
        assert len(group_ids) == 1, group_ids

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_user_invite_sends_invite(self, send_invite):
        invited_user = self._invite_user_to_group()

        assert send_invite.called
        assert send_invite.call_args[0][0].id == invited_user.id

    @mock.patch('ckan.lib.mailer.send_invite')
    @mock.patch('random.SystemRandom')
    def test_user_invite_works_even_if_username_already_exists(self, rand, _):
        rand.return_value.random.side_effect = [1000, 1000, 1000, 2000,
                                                3000, 4000, 5000]

        for _ in range(3):
            invited_user = self._invite_user_to_group(email='same@email.com')
            assert invited_user is not None, invited_user

    @mock.patch('ckan.lib.mailer.send_invite')
    @nose.tools.raises(ckan.logic.ValidationError)
    def test_user_invite_requires_email(self, _):
        self._invite_user_to_group(email=None)

    @mock.patch('ckan.lib.mailer.send_invite')
    @nose.tools.raises(ckan.logic.ValidationError)
    def test_user_invite_requires_role(self, _):
        self._invite_user_to_group(role=None)

    @mock.patch('ckan.lib.mailer.send_invite')
    @nose.tools.raises(ckan.logic.ValidationError)
    def test_user_invite_requires_group_id(self, _):
        self._invite_user_to_group(group={'id': None})

    def _invite_user_to_group(self, email='user@email.com',
                              group=None, role='member'):
        user = factories.User()
        group = group or factories.Group(user=user)

        context = {
            'user': user['name']
        }
        params = {
            'email': email,
            'group_id': group['id'],
            'role': role
        }

        result = helpers.call_action('user_invite', context, **params)

        return ckan.model.User.get(result['id'])


class TestResourceViewCreate(object):
    @classmethod
    def teardown_class(self):
        helpers.reset_db()

    def setup(self):
        helpers.reset_db()

    def test_resource_view_create(self):
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action('resource_view_create', context, **params)

        result.pop('id')
        result.pop('package_id')

        assert_equals(params, result)

    def test_resource_view_create_requires_resource_id(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop('resource_id')

        nose.tools.assert_raises(ckan.logic.ValidationError,
                                 helpers.call_action,
                                 'resource_view_create', context, **params)

    def test_resource_view_create_requires_title(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop('title')

        nose.tools.assert_raises(ckan.logic.ValidationError,
                                 helpers.call_action,
                                 'resource_view_create', context, **params)

    @mock.patch('ckan.lib.datapreview.get_view_plugin')
    def test_resource_view_create_requires_view_type(self, get_view_plugin):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop('view_type')

        get_view_plugin.return_value = 'mock_view_plugin'

        nose.tools.assert_raises(ckan.logic.ValidationError,
                                 helpers.call_action,
                                 'resource_view_create', context, **params)

    def test_resource_view_create_raises_if_couldnt_find_resource(self):
        context = {}
        params = self._default_resource_view_attributes(resource_id='unknown')
        nose.tools.assert_raises(ckan.logic.ValidationError,
                                 helpers.call_action,
                                 'resource_view_create', context, **params)

    def test_resource_view_create_raises_if_couldnt_find_view_extension(self):
        context = {}
        params = self._default_resource_view_attributes(view_type='unknown')
        nose.tools.assert_raises(ckan.logic.ValidationError,
                                 helpers.call_action,
                                 'resource_view_create', context, **params)

    def _default_resource_view_attributes(self, **kwargs):
        default_attributes = {
            'resource_id': factories.Resource()['id'],
            'view_type': 'image',
            'title': 'View',
            'description': 'A nice view'
        }

        default_attributes.update(kwargs)

        return default_attributes
