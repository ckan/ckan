# encoding: utf-8

import pytest
import six
from six import text_type
from ckan.lib.navl.dictization_functions import (
    validate, Invalid, check_dict, resolve_string_key, DataError,
    check_string_key, filter_glob_match, update_merge_dict,
    update_merge_string_key)


class TestValidate(object):
    def test_validate_passes_a_copy_of_the_context_to_validators(self):

        # We need to pass some keys on the context, otherwise validate
        # will do context = context || {}, which creates a new one, defeating
        # the purpose of this test
        context = {"foo": "bar"}

        def my_validator(key, data, errors, context_in_validator):

            assert not id(context) == id(context_in_validator)

        data_dict = {"my_field": "test"}

        schema = {"my_field": [my_validator]}

        data, errors = validate(data_dict, schema, context)

    def test_validate_adds_schema_keys_to_context(self):
        def my_validator(key, data, errors, context):

            assert "schema_keys" in context

            assert context["schema_keys"] == ["my_field"]

        data_dict = {"my_field": "test"}

        schema = {"my_field": [my_validator]}

        context = {}

        data, errors = validate(data_dict, schema, context)


class TestDictizationError(object):
    def test_str_error(self):
        err_obj = Invalid("Some ascii error")
        assert str(err_obj) == "Invalid: 'Some ascii error'"

    @pytest.mark.skipif(six.PY3, reason="Skip unicode checks in Py3")
    def test_unicode_error(self):
        err_obj = Invalid("Some ascii error")
        assert text_type(err_obj) == u"Invalid: 'Some ascii error'"

    def test_repr_error(self):
        err_obj = Invalid("Some ascii error")
        assert repr(err_obj) == "<Invalid 'Some ascii error'>"

    # Error msgs should be ascii, but let's just see what happens for unicode

    @pytest.mark.skipif(six.PY3, reason="Skip unicode checks in Py3")
    def test_str_unicode_error(self):
        err_obj = Invalid(u"Some unicode \xa3 error")
        assert str(err_obj) == "Invalid: u'Some unicode \\xa3 error'"

    @pytest.mark.skipif(six.PY3, reason="Skip unicode checks in Py3")
    def test_unicode_unicode_error(self):
        err_obj = Invalid(u"Some unicode \xa3 error")
        assert text_type(err_obj) == "Invalid: u'Some unicode \\xa3 error'"

    @pytest.mark.skipif(six.PY3, reason="Skip unicode checks in Py3")
    def test_repr_unicode_error(self):
        err_obj = Invalid(u"Some unicode \xa3 error")
        assert repr(err_obj) == "<Invalid u'Some unicode \\xa3 error'>"

    def test_str_blank(self):
        err_obj = Invalid("")
        assert str(err_obj) == "Invalid"

    @pytest.mark.skipif(six.PY3, reason="Skip unicode checks in Py3")
    def test_unicode_blank(self):
        err_obj = Invalid("")
        assert text_type(err_obj) == u"Invalid"

    def test_repr_blank(self):
        err_obj = Invalid("")
        assert repr(err_obj) == "<Invalid>"


class TestCheckDict(object):
    def test_exact(self):
        assert (
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'a': [{'b': 'c'}], 'd': 'e'})
            == [])

    def test_child(self):
        assert (
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'a': [{'b': 'c'}]})
            == [])

    def test_parent(self):
        assert (
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'d': 'e'})
            == [])

    def test_all_wrong(self):
        assert (
            check_dict(
                {'a': [{'b': 'c'}], 'd': 'e'},
                {'q': [{'b': 'c'}], 'a': [{'z': 'x'}], 'r': 'e'})
            == [('a', 0, 'z'), ('q',), ('r',)])

    def test_list_expected(self):
        assert (
            check_dict(
                {'a': [{'b': []}], 'd': 'e'},
                {'a': [{'b': {}}]})
            == [('a', 0, 'b')])

    def test_dict_expected(self):
        assert (
            check_dict(
                {'a': [{'b': []}], 'd': 'e'},
                {'a': [['b']]})
            == [('a', 0)])


class TestResolveStringKey(object):
    def test_dict_value(self):
        assert (
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__0__b')
            == ('c', ('a', 0, 'b')))

    def test_list_value(self):
        assert (
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__0')
            == ({'b': 'c'}, ('a', 0)))

    def test_bad_dict_value(self):
        with pytest.raises(DataError) as de:
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__0__c')
        assert de.value.error == 'Unmatched key a__0__c'

    def test_bad_list_value(self):
        with pytest.raises(DataError) as de:
            resolve_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__1__c')
        assert de.value.error == 'Unmatched key a__1'

    def test_partial_id_key(self):
        assert (
            resolve_string_key(
                {'a': [{'id': 'deadbeef', 'd': 'e'}]},
                'a__deadb__d')
            == ('e', ('a', 0, 'd')))

    def test_invalid_partial_id_key(self):
        with pytest.raises(DataError) as de:
            resolve_string_key(
                {'a': [{'id': 'deadbeef', 'd': 'e'}]},
                'a__dead__d')
        assert de.value.error == 'Unmatched key a__dead'


class TestCheckStringKey(object):
    def test_list_child(self):
        assert (
            check_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a',
                [{'b': 'c'}])
            == [])

    def test_string_child(self):
        assert (
            check_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'd',
                'e')
            == [])

    def test_all_wrong(self):
        assert (
            check_string_key(
                {'t': {'a': [{'b': 'c'}], 'd': 'e'}},
                't',
                {'q': [{'b': 'c'}], 'a': [{'z': 'x'}], 'r': 'e'})
            == [('t', 'a', 0, 'z'), ('t', 'q',), ('t', 'r',)])

    def test_child(self):
        assert (
            check_string_key(
                {'a': [{'b': 'c'}], 'd': 'e'},
                'a__0__b',
                'z')
            == [('a', 0, 'b')])

    def test_list_expected(self):
        assert (
            check_string_key(
                {'a': [{'b': []}], 'd': 'e'},
                'a__0__b',
                {})
            == [('a', 0, 'b')])

    def test_dict_expected(self):
        assert (
            check_string_key(
                {'a': [{'b': []}], 'd': 'e'},
                'a__0',
                ['b'])
            == [('a', 0)])


class TestFilterGlobMatch(object):
    def test_remove_leaves(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['q__0__b', 'q__1__z', 'r'])
        assert data == {'q': [{}, {}]}

    def test_remove_list_item(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['q__0'])
        assert data == {'q': [{'z': 'x'}], 'r': 'e'}

    def test_protect_list_item(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['+q__1', 'q__*'])
        assert data == {'q': [{'z': 'x'}], 'r': 'e'}

    def test_protect_dict_key(self):
        data = {'q': [{'b': 'c'}, {'z': 'x'}], 'r': 'e'}
        filter_glob_match(data, ['+q', '*'])
        assert data == {'q': [{'b': 'c'}, {'z': 'x'}]}

    def test_del_protect_del_dict(self):
        data = {'q': 'b', 'c': 'z', 'r': 'e'}
        filter_glob_match(data, ['q', '+*', 'r'])
        assert data == {'c': 'z', 'r': 'e'}

    def test_del_protect_del_list(self):
        data = [{'id': 'hello'}, {'id': 'world'}, {'id': 'people'}]
        filter_glob_match(data, ['world', '+*', 'hello'])
        assert data == [{'id': 'hello'}, {'id': 'people'}]


class TestMergeDict(object):
    def test_deep(self):
        data = {'a': [{'b': 'c'}], 'd': 'e'}
        update_merge_dict(data, {'q': [{'b': 'c'}], 'a': [{'z': 'x'}], 'r': 'e'})
        assert data == {'q': [{'b': 'c'}], 'a': [{'b': 'c', 'z': 'x'}], 'r': 'e', 'd': 'e'}

    def test_replace_child(self):
        data = {'a': [{'b': 'c'}], 'd': 'e'}
        update_merge_dict(data, {'a': [{'b': 'z'}]})
        assert data == {'a': [{'b': 'z'}], 'd': 'e'}

    def test_replace_parent(self):
        data = {'a': [{'b': 'c'}], 'd': 'e'}
        update_merge_dict(data, {'d': 'd'})
        assert data == {'a': [{'b': 'c'}], 'd': 'd'}

    def test_simple_list(self):
        data = {'a': ['q', 'w', 'e', 'r', 't']}
        update_merge_dict(data, {'a': ['z', 'x', 'c']})
        assert data == {'a': ['z', 'x', 'c', 'r', 't']}

    def test_list_expected(self):
        data = {'a': [{'b': []}], 'd': 'e'}
        with pytest.raises(DataError) as de:
            update_merge_dict(data, {'a': [{'b': {}}]})
        assert de.value.error == 'Expected list for a__0__b'

    def test_dict_expected(self):
        data = {'a': [{'b': []}], 'd': 'e'}
        with pytest.raises(DataError) as de:
            update_merge_dict(data, {'a': [['b']]})
        assert de.value.error == 'Expected dict for a__0'


class TestMergeStringKey(object):
    def test_replace_child(self):
        data = {'a': [{'b': 'c'}], 'd': 'e'}
        update_merge_string_key(data, 'a__0__b', 'z')
        assert data == {'a': [{'b': 'z'}], 'd': 'e'}

    def test_replace_parent(self):
        data = {'a': [{'b': 'c'}], 'd': 'e'}
        update_merge_string_key(data, 'd', 'd')
        assert data == {'a': [{'b': 'c'}], 'd': 'd'}

    def test_simple_list(self):
        data = {'a': ['q', 'w', 'e', 'r', 't']}
        update_merge_string_key(data, 'a__0', 'z')
        assert data == {'a': ['z', 'w', 'e', 'r', 't']}

    def test_list_expected(self):
        data = {'a': [{'b': []}], 'd': 'e'}
        with pytest.raises(DataError) as de:
            update_merge_string_key(data, 'a__0__b', {})
        assert de.value.error == 'Expected list for a__0__b'

    def test_dict_expected(self):
        data = {'a': [{'b': []}], 'd': 'e'}
        with pytest.raises(DataError) as de:
            update_merge_string_key(data, 'a__0', ['b'])
        assert de.value.error == 'Expected dict for a__0'
