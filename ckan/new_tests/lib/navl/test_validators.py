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
            key = ('foo',)
            if value == 'skip':
                data = {}
            else:
                data = {key: value}
            errors = {key: []}

            with nose.tools.assert_raises(df.StopOnError):
                validators.ignore_missing(
                    key=key,
                    data=data,
                    errors=errors,
                    context={})

            # ignore_missing should remove the item from the dict.
            assert key not in data

            # ignore_missing should not add any errors.
            assert errors[key] == []

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
