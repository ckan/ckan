'''Unit tests for ckan/logic/action/update.py.'''
import datetime

import nose.tools
import mock

import ckan.logic as logic
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


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

    def teardown(self):
        # Since some of the test methods below use the mock module to patch
        # things, we use this teardown() method to remove remove all patches.
        # (This makes sure the patches always get removed even if the test
        # method aborts with an exception or something.)
        mock.patch.stopall()

    def test_user_update_name(self):
        '''Test that updating a user's name works successfully.'''

        # The canonical form of a test has four steps:
        # 1. Setup any preconditions needed for the test.
        # 2. Call the function that's being tested, once only.
        # 3. Make assertions about the return value and/or side-effects of
        #    of the function that's being tested.
        # 4. Do absolutely nothing else!

        # 1. Setup.
        user = factories.User()

        # 2. Call the function that is being tested, once only.
        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password=factories.User.attributes()['password'],
                            name='updated',
                            )

        # 3. Make assertions about the return value and/or side-effects.
        updated_user = helpers.call_action('user_show', id=user['id'])
        # Note that we check just the field we were trying to update, not the
        # entire dict, only assert what we're actually testing.
        assert updated_user['name'] == 'updated'

        # 4. Do absolutely nothing else!

    def test_user_update_with_id_that_does_not_exist(self):
        user_dict = factories.User.attributes()
        user_dict['id'] = "there's no user with this id"

        with nose.tools.assert_raises(logic.NotFound):
            helpers.call_action('user_update', **user_dict)
        # TODO: Could assert the actual error message, not just the exception?
        # (Could also do this with many of the tests below.)

    def test_user_update_with_no_id(self):
        user_dict = factories.User.attributes()
        assert 'id' not in user_dict
        with nose.tools.assert_raises(logic.ValidationError):
            helpers.call_action('user_update', **user_dict)

    def test_user_update_with_invalid_name(self):
        user = factories.User()

        invalid_names = ('', 'a', False, 0, -1, 23, 'new', 'edit', 'search',
                         'a'*200, 'Hi!', )
        for name in invalid_names:
            user['name'] = name
            with nose.tools.assert_raises(logic.ValidationError):
                helpers.call_action('user_update', **user)

    def test_user_update_to_name_that_already_exists(self):
        fred = factories.User(name='fred')
        bob = factories.User(name='bob')

        # Try to update fred and change his user name to bob, which is already
        # bob's user name
        fred['name'] = bob['name']
        with nose.tools.assert_raises(logic.ValidationError):
            helpers.call_action('user_update', **fred)

    def test_user_update_password(self):
        '''Test that updating a user's password works successfully.'''

        user = factories.User()

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
        user = factories.User()

        user['password'] = 'xxx'  # This password is too short.
        with nose.tools.assert_raises(logic.ValidationError):
            helpers.call_action('user_update', **user)

    def test_user_update_with_empty_password(self):
        '''If an empty password is passed to user_update, nothing should
        happen.

        No error (e.g. a validation error) is raised, but the password is not
        changed either.

        '''
        user_dict = factories.User.attributes()
        original_password = user_dict['password']
        user_dict = factories.User(**user_dict)

        user_dict['password'] = ''
        helpers.call_action('user_update', **user_dict)

        import ckan.model as model
        updated_user = model.User.get(user_dict['id'])
        assert updated_user.validate_password(original_password)

    def test_user_update_with_null_password(self):
        user = factories.User()

        user['password'] = None
        with nose.tools.assert_raises(logic.ValidationError):
            helpers.call_action('user_update', **user)

    def test_user_update_with_invalid_password(self):
        user = factories.User()

        for password in (False, -1, 23, 30.7):
            user['password'] = password
            with nose.tools.assert_raises(logic.ValidationError):
                helpers.call_action('user_update', **user)

    # TODO: Valid and invalid values for the rest of the user model's fields.

    def test_user_update_activity_stream(self):
        '''Test that the right activity is emitted when updating a user.'''

        user = factories.User()
        before = datetime.datetime.now()

        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password=factories.User.attributes()['password'],
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
        '''Test that custom schemas passed to user_update do get used.

        user_update allows a custom validation schema to be passed to it in the
        context dict. This is just a simple test that if you pass a custom
        schema user_update does at least call a custom method that's given in
        the custom schema. We assume this means it did use the custom schema
        instead of the default one for validation, so user_update's custom
        schema feature does work.

        '''
        import ckan.logic.schema

        user = factories.User()

        # A mock validator method, it doesn't do anything but it records what
        # params it gets called with and how many times.
        mock_validator = mock.MagicMock()

        # Build a custom schema by taking the default schema and adding our
        # mock method to its 'id' field.
        schema = ckan.logic.schema.default_update_user_schema()
        schema['id'].append(mock_validator)

        # Call user_update and pass our custom schema in the context.
        # FIXME: We have to pass email and password even though we're not
        # trying to update them, or validation fails.
        helpers.call_action('user_update', context={'schema': schema},
                            id=user['name'], email=user['email'],
                            password=factories.User.attributes()['password'],
                            name='updated',
                            )

        # Since we passed user['name'] to user_update as the 'id' param,
        # our mock validator method should have been called once with
        # user['name'] as arg.
        mock_validator.assert_called_once_with(user['name'])

    def test_user_update_with_deferred_commit(self):
        '''Test that user_update()'s deferred_commit option works.

        In this test we mock out the rest of CKAN and test the user_update()
        action function in isolation. What we're testing is simply that when
        called with 'deferred_commit': True in its context, user_update() does
        not call ckan.model.repo.commit().

        '''
        # Patch ckan.model, so user_update will be accessing a mock object
        # instead of the real model.
        # It's ckan.logic.__init__.py:get_action() that actually adds the model
        # into the context dict, and that module does
        # `import ckan.model as model`, so what we actually need to patch is
        # 'ckan.logic.model' (the name that the model has when get_action()
        # accesses it), not 'ckan.model'.
        model_patch = mock.patch('ckan.logic.model')
        mock_model = model_patch.start()

        # Patch the validate() function, so validate() won't really be called
        # when user_update() calls it. update.py does
        # `_validate = ckan.lib.navl.dictization_functions.validate` so we
        # actually to patch this new name that's assigned to the function, not
        # its original name.
        validate_patch = mock.patch('ckan.logic.action.update._validate')
        mock_validate = validate_patch.start()

        # user_update() is going to call validate() with some params and it's
        # going to use the result that validate() returns. So we need to give
        # a mock validate function that will accept the right number of params
        # and return the right result.
        def mock_validate_function(data_dict, schema, context):
            '''Simply return the data_dict as given (without doing any
            validation) and an empty error dict.'''
            return data_dict, {}
        mock_validate.side_effect = mock_validate_function

        # Patch model_save, again update.py does
        # `import ckan.logic.action.update.model_save as model_save` so we
        # need to patch it by its new name
        # 'ckan.logic.action.update.model_save'.
        model_save_patch = mock.patch('ckan.logic.action.update.model_save')
        model_save_patch.start()

        # Patch model_dictize, again using the new name that update.py imports
        # it as.
        model_dictize_patch = mock.patch(
            'ckan.logic.action.update.model_dictize')
        model_dictize_patch.start()

        # Patch the get_action() function (using the name that update.py
        # assigns to it) with a default mock function that does nothing and
        # returns None.
        get_action_patch = mock.patch('ckan.logic.action.update._get_action')
        get_action_patch.start()

        # After all that patching, we can finally call user_update passing
        # 'defer_commit': True. The logic code in user_update will be run but
        # it'll have no effect because everything it calls is mocked out.
        helpers.call_action('user_update',
                            context={'defer_commit': True},
                            id='foobar', name='new_name',
                            )

        # Assert that user_update did *not* call our mock model object's
        # model.repo.commit() method.
        assert not mock_model.repo.commit.called
