'''Unit tests for ckan/logic/auth.update.py.

'''
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


class TestUpdate(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        import ckan.model as model
        model.repo.rebuild_db()

    # TODO: Probably all auth function tests want this? Move to helpers.py?
    def _call_auth(self, auth_name, context=None, **kwargs):
        '''Call a ckan.logic.auth function more conveniently for testing.

        '''
        import ckan.model
        import ckan.logic.auth.update
        if context is None:
            context = {}
        context.setdefault('user', '127.0.0.1')

        context.setdefault('model', ckan.model)

        # FIXME: Do we want to go through check_access() here?
        auth_function = ckan.logic.auth.update.__getattribute__(auth_name)
        return auth_function(context=context, data_dict=kwargs)

    def test_user_update_visitor_cannot_update_user(self):
        '''Visitors should not be able to update users' accounts.'''

        user = factories.User()
        user['name'] = 'updated'

        # Try to update the user, but without passing any API key.
        result = self._call_auth('user_update', **user)
        assert result['success'] is False

        # TODO: Assert result['msg'] as well? In this case the message is not
        # very sensible: "User 127.0.0.1 is not authorized to edit user foo".
        # Also applies to the rest of these tests.

    def test_user_update_user_cannot_update_another_user(self):
        '''Users should not be able to update other users' accounts.'''

        fred = factories.User(name='fred')
        bob = factories.User(name='bob')
        fred['name'] = 'updated'

        # Make Bob try to update Fred's user account.
        context = {'user': bob['name']}
        result = self._call_auth('user_update', context=context, **fred)
        assert result['success'] is False

    def test_user_update_user_can_update_herself(self):
        '''Users should be authorized to update their own accounts.'''

        user = factories.User()

        context = {'user': user['name']}
        user['name'] = 'updated'
        result = self._call_auth('user_update', context=context, **user)
        assert result['success'] is True
