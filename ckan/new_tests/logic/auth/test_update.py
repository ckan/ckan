'''Unit tests for ckan/logic/auth.update.py.

'''
import mock
import nose

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.logic as logic


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

    ## START-AFTER

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

    ## END-BEFORE

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

    # TODO: Tests for user_update's reset_key behavior.
