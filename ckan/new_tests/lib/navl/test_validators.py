'''Unit tests for ckan/lib/navl/validators.py.

'''
import nose.tools


class TestValidators(object):

    def test_ignore_missing_with_value_missing(self):
        '''If data[key] is None or dictization_functions.missing or if
        key is not in data, then ignore_missing() should raise StopOnError.'''

        import ckan.lib.navl.dictization_functions as df
        import ckan.lib.navl.validators as validators

        for value in (None, df.missing, 'skip'):

            # This is the key for the value that is going to be validated.
            key = ('key to be validated',)

            # This is another random key that's going to be in the data and
            # errors dict just so we can test that ignore_missing() doesn't
            # modify it.
            other_key = ('other key',)

            if value == 'skip':
                data = {}
            else:
                data = {key: value}

            # Add some other random stuff into data, just so we can test that
            # ignore_missing() doesn't modify it.
            data[other_key] = 'other value'

            errors = {key: []}

            # Add some other random errors into errors, just so we can test
            # that ignore_missing doesn't modify them.
            errors[other_key] = ['other error']

            with nose.tools.assert_raises(df.StopOnError):
                validators.ignore_missing(
                    key=key,
                    data=data,
                    errors=errors,
                    context={})

            # ignore_missing should remove the key being validated from the
            # dict, but it should not remove other keys or add any keys.
            assert data == {other_key: 'other value'}

            # ignore_missing shouldn't modify the errors dict.
            assert errors == {key: [], other_key: ['other error']}

    def test_ignore_missing_with_a_value(self):
        '''If data[key] is neither None or missing, ignore_missing() should do
        nothing.

        '''
        import ckan.lib.navl.validators as validators

        key = ('foo',)
        data = {key: 'bar'}
        errors = {key: []}

        result = validators.ignore_missing(key=key, data=data, errors=errors,
                                           context={})

        assert result is None

        # ignore_missing shouldn't remove or modify the value.
        assert data.get(key) == 'bar'

        # ignore_missing shouldn't add any errors.
        assert errors[key] == []
