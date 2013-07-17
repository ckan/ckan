'''Unit tests for ckan/logic/action/update.py.

'''
import nose.tools

import ckan.logic as logic
import ckan.new_tests.helpers as helpers
import ckan.new_tests.data as data


class TestClass(object):

    @classmethod
    def setup_class(cls):
        # Initialize the test db (if it isn't already) and clean out any data
        # left in it.
        helpers.reset_db()

    def setup(self):
        import ckan.model as model
        # Reset the db before each test method.
        model.repo.rebuild_db()

    def test_update_user_name(self):
        '''Test that updating a user's name works successfully.'''

        # The canonical form of a test has four steps:
        # 1. Setup anything preconditions needed for the test.
        # 2. Call the function that's being tested, once only.
        # 3. Make assertions about the return value and/or side-effects of
        #    of the function that's being tested.
        # 4. Do absolutely nothing else!

        # 1. Setup.
        user = helpers.call_action('user_create', **data.TYPICAL_USER)

        # 2. Call the function that is being tested, once only.
        # Note we have to pass the email address and password (in plain text!)
        # to user_update even though we're not updating those fields, otherwise
        # validation fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password=data.TYPICAL_USER['password'],
                            name='updated',
                            )

        # 3. Make assertions about the return value and/or side-effects.
        updated_user = helpers.call_action('user_show', id=user['id'])
        # Note that we check just the field we were trying to update, not the
        # entire dict, only assert what we're actually testing.
        assert updated_user['name'] == 'updated'

        # 4. Do absolutely nothing else!

    def test_user_update_with_id_that_does_not_exist(self):
        # FIXME: Does this need to be more realistic?
        # - Actually create a user before trying to update it with the wrong
        #   id?
        # - Actually pass other params (name, about..) to user_update?
        with nose.tools.assert_raises(logic.NotFound) as context:
            helpers.call_action('user_update',
                                id="there's no user with this id")
        # TODO: Could assert the actual error message, not just the exception?
        # (Could also do this with many of the tests below.)

    def test_user_update_with_no_id(self):
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update')

    def test_user_update_with_invalid_name(self):
        user = helpers.call_action('user_create', **data.TYPICAL_USER)

        # FIXME: This actually breaks the canonical test form rule by calling
        # the function-under-test multiple times.
        # Breaking this up into multiple tests would actually be clearer in
        # terms of each test testing one thing and the names of the test
        # methods documenting what the test does and how the function is
        # supposed to behave.
        # BUT the test code would be very repetitive.
        invalid_names = ('', 'a', False, 0, -1, 23, 'new', 'edit', 'search',
                         'a'*200, 'Hi!', )
        for name in invalid_names:
            user['name'] = name
            with nose.tools.assert_raises(logic.ValidationError) as context:
                helpers.call_action('user_update', **user)

    def test_user_update_to_name_that_already_exists(self):
        fred = helpers.call_action('user_create', **data.TYPICAL_USER)
        bob = helpers.call_action('user_create', name='bob',
                                   email='bob@bob.com', password='pass')

        # Try to update fred and change his user name to bob, which is already
        # bob's user name
        fred['name'] = bob['name']
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **fred)

    def test_update_user_password(self):
        '''Test that updating a user's password works successfully.'''

        user = helpers.call_action('user_create', **data.TYPICAL_USER)

        # Note we have to pass the email address to user_update even though
        # we're not updating it, otherwise validation fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password='new password',
                            )

        # user_show() never returns the user's password, so we have to access
        # the model directly to test it.
        import ckan.model as model
        updated_user = model.User.get(user['id'])
        assert updated_user.validate_password('new password')

    def test_user_update_with_short_password(self):
        user = helpers.call_action('user_create', **data.TYPICAL_USER)

        user['password'] = 'xxx'  # This password is too short.
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **user)

    def test_user_update_with_empty_password(self):
        user = helpers.call_action('user_create', **data.TYPICAL_USER)

        user['password'] = ''
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **user)

    def test_user_update_with_null_password(self):
        user = helpers.call_action('user_create', **data.TYPICAL_USER)

        user['password'] = None
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **user)

    # TODO: Valid and invalid values for the rest of the user model's fields.

    def test_user_update_activity_stream(self):
        pass

    def test_user_update_with_custom_schema(self):
        pass

    def test_user_update_with_deferred_commit(self):
        pass
