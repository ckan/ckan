'''Unit tests for ckan/logic/action/update.py.

Notes:

- All user_update tests are named test_user_update_*

- Using the canonical test form from the Pylons guidelines
  (i.e. each method tests One Thing and the method name explains what it tests)

- Not testing auth here, that can be done in ckan.tests.logic.auth.*.py

- But I am testing validation here, because some action functions do some of
  their own validation, not all the validation is done in the schemas

- The tests for each action function try to cover:
  - Testing for success:
    - Typical values
    - Edge cases
    - Multiple parameters in different combinations
  - Testing for failure:
    - Common mistakes
    - Bizarre input
    - Unicode

- Cover the interface of the function (i.e. test all params and features)

- Not storing anything (e.g. test data) against self in the test class,
  instead have each test method call helper functions to get any test data
  it needs

  - I think it would be okay to create *read-only* data against self in
    setup_class though

- The tests are not ordered, and each one can be run on its own (db is rebuilt
  after each test method)

- Within reason, keep tests as clear and simple as possible even if it means
  they get repetitive

'''
import datetime
import nose.tools

import ckan.logic as logic
import ckan.new_tests.helpers as helpers
import ckan.new_tests.data as data


def datetime_from_string(s):
    '''Return a standard datetime.datetime object initialised from a string in
    the same format used for timestamps in dictized activities (the format
    produced by datetime.datetime.isoformat())

    '''
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')


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

    def test_user_update_name(self):
        '''Test that updating a user's name works successfully.'''

        # The canonical form of a test has four steps:
        # 1. Setup any preconditions needed for the test.
        # 2. Call the function that's being tested, once only.
        # 3. Make assertions about the return value and/or side-effects of
        #    of the function that's being tested.
        # 4. Do absolutely nothing else!

        # 1. Setup.
        user = helpers.call_action('user_create', **data.typical_user())

        # 2. Call the function that is being tested, once only.
        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password=data.typical_user()['password'],
                            name='updated',
                            )

        # 3. Make assertions about the return value and/or side-effects.
        updated_user = helpers.call_action('user_show', id=user['id'])
        # Note that we check just the field we were trying to update, not the
        # entire dict, only assert what we're actually testing.
        assert updated_user['name'] == 'updated'

        # 4. Do absolutely nothing else!

    def test_user_update_with_id_that_does_not_exist(self):
        user_dict = data.typical_user()
        user_dict['id'] = "there's no user with this id"
        with nose.tools.assert_raises(logic.NotFound) as context:
            helpers.call_action('user_update', **user_dict)
        # TODO: Could assert the actual error message, not just the exception?
        # (Could also do this with many of the tests below.)

    def test_user_update_with_no_id(self):
        user_dict = data.typical_user()
        assert 'id' not in user_dict
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **user_dict)

    def test_user_update_with_invalid_name(self):
        user = helpers.call_action('user_create', **data.typical_user())

        invalid_names = ('', 'a', False, 0, -1, 23, 'new', 'edit', 'search',
                         'a'*200, 'Hi!', )
        for name in invalid_names:
            user['name'] = name
            with nose.tools.assert_raises(logic.ValidationError) as context:
                helpers.call_action('user_update', **user)

    def test_user_update_to_name_that_already_exists(self):
        fred = helpers.call_action('user_create', **data.typical_user())
        bob = helpers.call_action('user_create', name='bob',
                                   email='bob@bob.com', password='pass')

        # Try to update fred and change his user name to bob, which is already
        # bob's user name
        fred['name'] = bob['name']
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **fred)

    def test_user_update_password(self):
        '''Test that updating a user's password works successfully.'''

        user = helpers.call_action('user_create', **data.typical_user())

        # FIXME we have to pass the email address to user_update even though
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
        user = helpers.call_action('user_create', **data.typical_user())

        user['password'] = 'xxx'  # This password is too short.
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **user)

    def test_user_update_with_empty_password(self):
        user = helpers.call_action('user_create', **data.typical_user())

        user['password'] = ''
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **user)

    def test_user_update_with_null_password(self):
        user = helpers.call_action('user_create', **data.typical_user())

        user['password'] = None
        with nose.tools.assert_raises(logic.ValidationError) as context:
            helpers.call_action('user_update', **user)

    def test_user_update_with_invalid_password(self):
        user = helpers.call_action('user_create', **data.typical_user())

        for password in (False, -1, 23, 30.7):
            user['password'] = password
            with nose.tools.assert_raises(logic.ValidationError) as context:
                helpers.call_action('user_update', **user)

    # TODO: Valid and invalid values for the rest of the user model's fields.

    def test_user_update_activity_stream(self):
        '''Test that the right activity is emitted when updating a user.'''

        user = helpers.call_action('user_create', **data.typical_user())
        before = datetime.datetime.now()

        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password=data.typical_user()['password'],
                            name='updated',
                            )

        activity_stream = helpers.call_action('user_activity_list',
                                              id=user['id'])
        latest_activity = activity_stream[0]
        assert latest_activity['activity_type'] == 'changed user'
        assert latest_activity['object_id'] == user['id']
        assert latest_activity['user_id'] == user['id']
        after = datetime.datetime.now()
        timestamp = datetime_from_string(latest_activity['timestamp'])
        assert timestamp >= before and timestamp <= after

    def test_user_update_with_custom_schema(self):
        pass

    def test_user_update_with_deferred_commit(self):
        pass
