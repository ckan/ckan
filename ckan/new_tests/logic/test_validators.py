# -*- coding: utf-8 -*-
'''Unit tests for ckan/logic/validators.py.

'''
import copy

import mock
import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.data as test_data


class TestValidators(object):

    @classmethod
    def setup_class(cls):
        # Initialize the test db (if it isn't already) and clean out any data
        # left in it.
        helpers.reset_db()

    def setup(self):
        import ckan.model as model
        # Reset the db before each test method.
        model.repo.rebuild_db()

    def test_name_validator_with_invalid_value(self):
        '''If given an invalid value name_validator() should do raise Invalid.

        '''
        import ckan.logic.validators as validators
        import ckan.lib.navl.dictization_functions as df
        import ckan.model as model

        invalid_values = [
            # Non-string names aren't allowed as names.
            13,
            23.7,
            100L,
            1.0j,
            None,
            True,
            False,
            ('a', 2, False),
            [13, None, True],
            {'foo': 'bar'},
            lambda x: x**2,

            # Certain reserved strings aren't allowed as names.
            'new',
            'edit',
            'search',

            # Strings < 2 characters long aren't allowed as names.
            '',
            'a',
            '2',

            # Strings > PACKAGE_NAME_MAX_LENGTH long aren't allowed as names.
            'a' * (model.PACKAGE_NAME_MAX_LENGTH + 1),

            # Strings containing non-ascii characters aren't allowed as names.
            u"fred_❤%'\"Ußabc@fred.com",

            # Strings containing upper-case characters aren't allowed as names.
            'seanH',

            # Strings containing spaces aren't allowed as names.
            'sean h',

            # Strings containing punctuation aren't allowed as names.
            'seanh!',
        ]

        for invalid_value in invalid_values:
            with nose.tools.assert_raises(df.Invalid):
                validators.name_validator(invalid_value, context={})

    def test_name_validator_with_valid_value(self):
        '''If given a valid string name_validator() should do nothing and
        return the string.

        '''
        import ckan.logic.validators as validators
        import ckan.model as model

        valid_names = [
            'fred',
            'fred-flintstone',
            'fred_flintstone',
            'fred_flintstone-9',
            'f' * model.PACKAGE_NAME_MAX_LENGTH,
            '-' * model.PACKAGE_NAME_MAX_LENGTH,
            '_' * model.PACKAGE_NAME_MAX_LENGTH,
            '9' * model.PACKAGE_NAME_MAX_LENGTH,
            '99',
            '--',
            '__',
            u'fred-flintstone_9',
        ]

        for valid_name in valid_names:
            result = validators.name_validator(valid_name, context={})
            assert result == valid_name, ('If given a valid string '
                'name_validator() should return the string unmodified.')

    def test_user_name_validator_with_non_string_value(self):
        '''user_name_validator() should raise Invalid if given a non-string
        value.

        '''
        import ckan.logic.validators as validators
        import ckan.lib.navl.dictization_functions as df

        non_string_values = [
            13,
            23.7,
            100L,
            1.0j,
            None,
            True,
            False,
            ('a', 2, False),
            [13, None, True],
            {'foo': 'bar'},
            lambda x: x**2,
        ]

        # Mock ckan.model.
        mock_model = mock.MagicMock()
        # model.User.get(some_user_id) needs to return None for this test.
        mock_model.User.get.return_value = None

        key = ('name',)
        for non_string_value in non_string_values:
            data = test_data.validator_data_dict()
            data[key] = non_string_value
            errors = test_data.validator_errors_dict()
            errors[key] = []

            # Make copies of the data and errors dicts for asserting later.
            original_data = copy.deepcopy(data)
            original_errors = copy.deepcopy(errors)

            with nose.tools.assert_raises(df.Invalid):
                validators.user_name_validator(key, data, errors,
                                               context={'model': mock_model})

            assert data == original_data, ("user_name_validator shouldn't "
                                           'modify the data dict')

            assert errors == original_errors, ("user_name_validator shouldn't "
                                               'modify the errors dict')

    def test_user_name_validator_with_a_name_that_already_exists(self):
        '''user_name_validator() should add to the errors dict if given a
        user name that already exists.

        '''
        import ckan.logic.validators as validators

        # Mock ckan.model. model.User.get('user_name') will return another mock
        # object rather than None, which will simulate an existing user with
        # the same user name in the database.
        mock_model = mock.MagicMock()

        data = test_data.validator_data_dict()
        key = ('name',)
        data[key] = 'user_name'
        errors = test_data.validator_errors_dict()
        errors[key] = []

        # Make copies of the data and errors dicts for asserting later.
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)

        # Try to create another user with the same name as the existing user.
        result = validators.user_name_validator(key, data, errors,
                                                context={'model': mock_model})

        assert result is None, ("user_name_validator() shouldn't return "
                                "anything")

        msg = 'That login name is not available.'
        assert errors[key] == [msg], ('user_name_validator() should add to '
                                      'the errors dict when given the name of '
                                      'a user that already exists')

        errors[key] = []
        assert errors == original_errors, ('user_name_validator() should not '
                                           'modify other parts of the errors '
                                           'dict')

        assert data == original_data, ('user_name_validator() should not '
                                       'modify the data dict')

    def test_user_name_validator_successful(self):
        '''user_name_validator() should do nothing if given a valid name.'''

        import ckan.logic.validators as validators

        data = test_data.validator_data_dict()
        key = ('name',)
        data[key] = 'new_user_name'
        errors = test_data.validator_errors_dict()
        errors[key] = []

        # Mock ckan.model.
        mock_model = mock.MagicMock()
        # model.User.get(user_name) should return None, to simulate that no
        # user with that name exists in the database.
        mock_model.User.get.return_value = None

        # Make copies of the data and errors dicts for asserting later.
        original_data = copy.deepcopy(data)
        original_errors = copy.deepcopy(errors)

        result = validators.user_name_validator(key, data, errors,
                                                context={'model': mock_model})

        assert result is None, ("user_name_validator() shouldn't return "
                                'anything')

        assert data == original_data, ("user_name_validator shouldn't modify "
                                       'the data dict')

        assert errors == original_errors, ("user_name_validator shouldn't "
                                           'modify the errors dict if given a'
                                           'valid user name')

    # TODO: Test user_name_validator()'s behavior when there's a 'user_obj' in
    # the context dict.
