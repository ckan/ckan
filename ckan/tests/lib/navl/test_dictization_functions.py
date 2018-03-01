# encoding: utf-8

import nose
from six import text_type
from ckan.lib.navl.dictization_functions import validate, Invalid


eq_ = nose.tools.eq_


class TestValidate(object):

    def test_validate_passes_a_copy_of_the_context_to_validators(self):

        # We need to pass some keys on the context, otherwise validate
        # will do context = context || {}, which creates a new one, defeating
        # the purpose of this test
        context = {'foo': 'bar'}

        def my_validator(key, data, errors, context_in_validator):

            assert not id(context) == id(context_in_validator)

        data_dict = {
            'my_field': 'test',
        }

        schema = {
            'my_field': [my_validator],
        }

        data, errors = validate(data_dict, schema, context)

    def test_validate_adds_schema_keys_to_context(self):

        def my_validator(key, data, errors, context):

            assert 'schema_keys' in context

            eq_(context['schema_keys'], ['my_field'])

        data_dict = {
            'my_field': 'test',
        }

        schema = {
            'my_field': [my_validator],
        }

        context = {}

        data, errors = validate(data_dict, schema, context)


class TestDictizationError(object):

    def test_str_error(self):
        err_obj = Invalid('Some ascii error')
        eq_(str(err_obj), "Invalid: 'Some ascii error'")

    def test_unicode_error(self):
        err_obj = Invalid('Some ascii error')
        eq_(text_type(err_obj), u"Invalid: 'Some ascii error'")

    def test_repr_error(self):
        err_obj = Invalid('Some ascii error')
        eq_(repr(err_obj), "<Invalid 'Some ascii error'>")

    # Error msgs should be ascii, but let's just see what happens for unicode

    def test_str_unicode_error(self):
        err_obj = Invalid(u'Some unicode \xa3 error')
        eq_(str(err_obj), "Invalid: u'Some unicode \\xa3 error'")

    def test_unicode_unicode_error(self):
        err_obj = Invalid(u'Some unicode \xa3 error')
        eq_(text_type(err_obj), "Invalid: u'Some unicode \\xa3 error'")

    def test_repr_unicode_error(self):
        err_obj = Invalid(u'Some unicode \xa3 error')
        eq_(repr(err_obj), "<Invalid u'Some unicode \\xa3 error'>")

    def test_str_blank(self):
        err_obj = Invalid('')
        eq_(str(err_obj), "Invalid")

    def test_unicode_blank(self):
        err_obj = Invalid('')
        eq_(text_type(err_obj), u"Invalid")

    def test_repr_blank(self):
        err_obj = Invalid('')
        eq_(repr(err_obj), "<Invalid>")
