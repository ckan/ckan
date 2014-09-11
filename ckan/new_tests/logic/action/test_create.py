'''Unit tests for ckan/logic/auth/create.py.

'''

import mock
import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.model as model
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

        return model.User.get(result['id'])


class TestMemberCreate(object):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_group_member_creation(self):
        user = factories.User()
        group = factories.Group()

        new_membership = helpers.call_action(
            'group_member_create',
            id=group['id'],
            username=user['name'],
            role='member',
        )

        assert_equals(new_membership['group_id'], group['id'])
        assert_equals(new_membership['table_name'], 'user')
        assert_equals(new_membership['table_id'], user['id'])
        assert_equals(new_membership['capacity'], 'member')

    def test_organization_member_creation(self):
        user = factories.User()
        organization = factories.Organization()

        new_membership = helpers.call_action(
            'organization_member_create',
            id=organization['id'],
            username=user['name'],
            role='member',
        )

        assert_equals(new_membership['group_id'], organization['id'])
        assert_equals(new_membership['table_name'], 'user')
        assert_equals(new_membership['table_id'], user['id'])
        assert_equals(new_membership['capacity'], 'member')
