# encoding: utf-8

from nose.tools import eq_, assert_raises
from six import text_type
from ckan.lib.navl.dictization_functions import (
    validate, Invalid, check_dict, resolve_string_key, DataError,
    check_string_key, filter_glob_match)


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


class TestCheckDict(object):
    def test_exact(self):
        eq_(
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'a': [{'b': 'c'}], 'd': 'e'}),
            [])

    def test_child(self):
        eq_(
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'a': [{'b': 'c'}]}),
            [])

    def test_parent(self):
        eq_(
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'d': 'd'}),
            [])

    def test_all_wrong(self):
        eq_(
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'q': [{'b': 'c'}], 'a': [{'z': 'x'}], 'r': 'e'}),
            [('a', 0, 'z'), ('q',), ('r',)])

    def test_child(self):
        eq_(
            check_dict(
                {'a':[{'b': 'c'}], 'd':'e'},
                {'a':[{'b': 'z'}], 'd':'e'}),
            [('a', 0, 'b')])

    def test_parent(self):
        eq_(
            check_dict(
                {'a':[{'b': 'c'}], 'd':'e'},
                {'a':[{'b': 'c'}], 'd':'d'}),
            [('d',)])

    def test_list_expected(self):
        eq_(
            check_dict(
                {'a':[{'b': []}], 'd':'e'},
                {'a':[{'b': {}}]}),
            [('a', 0, 'b')])

    def test_dict_expected(self):
        eq_(
            check_dict(
                {'a':[{'b': []}], 'd':'e'},
                {'a':[['b']]}),
            [('a', 0)])


class TestResolveStringKey(object):
    def test_dict_value(self):
        eq_(
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__0__b'),
            ('c', ('a', 0, 'b')))

    def test_list_value(self):
        eq_(
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__0'),
            ({'b': 'c'}, ('a', 0)))

    def test_bad_dict_value(self):
        with assert_raises(DataError) as de:
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__0__c'),
        eq_(de.exception.error, 'Unmatched key a__0__c')

    def test_bad_list_value(self):
        with assert_raises(DataError) as de:
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__1__c'),
        eq_(de.exception.error, 'Unmatched key a__1')

    def test_partial_id_key(self):
        eq_(
            resolve_string_key(
                {'a': [{'id': 'deadbeef', 'd': 'e'}]},
                'a__deadb__d'),
            ('e', ('a', 0, 'd')))

    def test_invalid_partial_id_key(self):
        with assert_raises(DataError) as de:
            resolve_string_key(
                {'a': [{'id': 'deadbeef', 'd': 'e'}]},
                'a__dead__d'),
        eq_(de.exception.error, 'Unmatched key a__dead')


class TestCheckStringKey(object):
    def test_list_child(self):
        eq_(
            check_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a',
                [{'b': 'c'}]),
            [])

    def test_string_child(self):
        eq_(
            check_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'd',
                'e'),
            [])

    def test_all_wrong(self):
        eq_(
            check_string_key(
                {'t': {'a': [{'b': 'c'}], 'd': 'e'}},
                't',
                {'q': [{'b': 'c'}], 'a': [{'z': 'x'}], 'r': 'e'}),
            [('t', 'a', 0, 'z'), ('t', 'q',), ('t', 'r',)])

    def test_child(self):
        eq_(
            check_string_key(
                {'a':[{'b': 'c'}], 'd':'e'},
                'a__0__b',
                'z'),
            [('a', 0, 'b')])

    def test_list_expected(self):
        eq_(
            check_string_key(
                {'a':[{'b': []}], 'd':'e'},
                'a__0__b',
                {}),
            [('a', 0, 'b')])

    def test_dict_expected(self):
        eq_(
            check_string_key(
                {'a':[{'b': []}], 'd':'e'},
                'a__0',
                ['b']),
            [('a', 0)])


class TestFilterGlobMatch(object):
    def test_remove_leaves(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['q__0__b', 'q__1__z', 'r'])
        eq_(data, {'q': [{}, {}]})

    def test_remove_list_item(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['q__0'])
        eq_(data, {'q': [{'z': 'x'}], 'r': 'e'})

    def test_protect_list_item(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['+q__1', 'q__*'])
        eq_(data, {'q': [{'z': 'x'}], 'r': 'e'})

    def test_protect_dict_key(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['+q', '*'])
        eq_(data, {'q': [{'b': 'c'}, {'z': 'x'}]})

    def test_del_protect_del_dict(self):
        data = {'q': 'b', 'c': 'z', 'r': 'e'}
        filter_glob_match(data, ['q', '+*', 'r'])
        eq_(data, {'c': 'z', 'r': 'e'})

    def test_del_protect_del_list(self):
        data = [{'id': 'hello'}, {'id': 'world'}, {'id': 'people'}]
        filter_glob_match(data, ['world', '+*', 'hello'])
        eq_(data, [{'id': 'hello'}, {'id': 'people'}])
