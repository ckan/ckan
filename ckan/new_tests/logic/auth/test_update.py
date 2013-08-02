'''Unit tests for ckan/logic/auth.update.py.

'''
import mock


class TestUpdate(object):

    # TODO: Probably all auth function tests want this? Move to helpers.py?
    def _call_auth(self, auth_name, context=None, **kwargs):
        '''Call a ckan.logic.auth function more conveniently for testing.

        '''
        import ckan.logic.auth.update

        assert 'user' in context, ('Test methods must put a user name in the '
                                   'context dict')
        assert 'model' in context, ('Test methods must put a model in the '
                                    'context dict')

        # FIXME: Do we want to go through check_access() here?
        auth_function = ckan.logic.auth.update.__getattribute__(auth_name)
        return auth_function(context=context, data_dict=kwargs)

    def test_user_update_visitor_cannot_update_user(self):
        '''Visitors should not be able to update users' accounts.'''

        # Make a mock ckan.model.User object, Fred.
        fred = mock.MagicMock()
        # Give the mock user object some attributes it's going to need.
        fred.reset_key = 'fred_reset_key'
        fred.id = 'fred_user_id'
        fred.name = 'fred'

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
        result = self._call_auth('user_update', context=context, **params)

        assert result['success'] is False

    def test_user_update_user_cannot_update_another_user(self):
        '''Users should not be able to update other users' accounts.'''

        # Make a mock ckan.model.User object, Fred.
        fred = mock.MagicMock()
        # Give the mock user object some attributes it's going to need.
        fred.reset_key = 'fred_reset_key'
        fred.id = 'fred_user_id'
        fred.name = 'fred'

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return Fred.
        mock_model.User.get.return_value = fred

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.
        context = {'model': mock_model}

        # The logged-in user is going to be Bob, not Fred.
        context['user'] = 'bob'

        # Make Bob try to update Fred's user account.
        params = {
            'id': fred.id,
            'name': 'updated_user_name',
        }
        result = self._call_auth('user_update', context=context, **params)

        assert result['success'] is False

    def test_user_update_user_can_update_herself(self):
        '''Users should be authorized to update their own accounts.'''

        # Make a mock ckan.model.User object, Fred.
        fred = mock.MagicMock()
        # Give the mock user object some attributes it's going to need.
        fred.reset_key = 'fred_reset_key'
        fred.id = 'fred_user_id'
        fred.name = 'fred'

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
        result = self._call_auth('user_update', context=context, **params)

        assert result['success'] is True

    def test_user_update_with_no_user_in_context(self):

        # Make a mock ckan.model.User object.
        mock_user = mock.MagicMock()
        # Give the mock user object some attributes it's going to need.
        mock_user.reset_key = 'mock reset key'
        mock_user.id = 'mock user id'
        mock_user.name = 'mock_user'

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
        result = self._call_auth('user_update', context=context, **params)

        assert result['success'] is False

    # TODO: Tests for user_update's reset_key behavior.
