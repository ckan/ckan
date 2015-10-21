import nose
from ckan.lib.navl.dictization_functions import validate


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
