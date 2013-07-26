# -*- coding: utf-8 -*-
'''Unit tests for ckan/logic/validators.py.

'''
import nose.tools


class TestValidators(object):

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
