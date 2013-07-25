'''Unit tests for ckan/lib/navl/validators.py.

'''
import nose.tools


class TestValidators(object):

    def test_ignore_missing_with_None(self):
        '''If data[key] is None ignore_missing() should raise StopOnError.'''

        import ckan.lib.navl.dictization_functions as df
        import ckan.lib.navl.validators as validators

        key = ('foo',)
        data = {key: None}
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

    def test_ignore_missing_with_missing(self):
        '''If data[key] is missing ignore_missing() should raise StopOnError.

        '''
        import ckan.lib.navl.dictization_functions as df
        import ckan.lib.navl.validators as validators

        key = ('foo',)
        data = {key: df.missing}
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

    def test_ignore_missing_without_key(self):
        '''If key is not in data ignore_missing() should raise StopOnError.'''

        import ckan.lib.navl.dictization_functions as df
        import ckan.lib.navl.validators as validators

        key = ('foo',)
        data = {}
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
