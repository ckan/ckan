# encoding: utf-8

import pytest

from pprint import pformat
from ckan.lib.navl.dictization_functions import (
    validate,
    Invalid,
    check_dict,
    resolve_string_key,
    DataError,
    check_string_key,
    filter_glob_match,
    update_merge_dict,
    update_merge_string_key,
    flatten_schema,
    get_all_key_combinations,
    make_full_schema,
    flatten_dict,
    unflatten,
    missing,
    augment_data,
    _validate,
)

from ckan.lib.navl.validators import (
    empty,
    unicode_safe,
    not_empty,
    ignore_missing,
    default,
    convert_int,
    ignore,
)


def identity_converter(key, data, errors, context):
    """This validator removes `__`-fields and leaves everything else.
    """
    return


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

    def test_repr_error(self):
        err_obj = Invalid("Some ascii error")
        assert repr(err_obj) == "<Invalid 'Some ascii error'>"

    # Error msgs should be ascii, but let's just see what happens for unicode

    def test_str_blank(self):
        err_obj = Invalid("")
        assert str(err_obj) == "Invalid"


class TestCheckDict(object):
    def test_exact(self):
        assert (
            check_dict(
                {"a": [{"b": "c"}], "d": "e"}, {"a": [{"b": "c"}], "d": "e"}
            )
            == []
        )

    def test_child(self):
        assert (
            check_dict({"a": [{"b": "c"}], "d": "e"}, {"a": [{"b": "c"}]})
            == []
        )

    def test_parent(self):
        assert check_dict({"a": [{"b": "c"}], "d": "e"}, {"d": "e"}) == []

    def test_all_wrong(self):
        assert (
            check_dict(
                {"a": [{"b": "c"}], "d": "e"},
                {"q": [{"b": "c"}], "a": [{"z": "x"}], "r": "e"},
            )
            == [("a", 0, "z"), ("q",), ("r",)]
        )

    def test_list_expected(self):
        assert check_dict(
            {"a": [{"b": []}], "d": "e"}, {"a": [{"b": {}}]}
        ) == [("a", 0, "b")]

    def test_dict_expected(self):
        assert check_dict({"a": [{"b": []}], "d": "e"}, {"a": [["b"]]}) == [
            ("a", 0)
        ]


class TestResolveStringKey(object):
    def test_dict_value(self):
        assert resolve_string_key(
            {"a": [{"b": "c"}], "d": "e"}, "a__0__b"
        ) == ("c", ("a", 0, "b"))

    def test_list_value(self):
        assert resolve_string_key({"a": [{"b": "c"}], "d": "e"}, "a__0") == (
            {"b": "c"},
            ("a", 0),
        )

    def test_bad_dict_value(self):
        with pytest.raises(DataError) as de:
            resolve_string_key({"a": [{"b": "c"}], "d": "e"}, "a__0__c")
        assert de.value.error == "Unmatched key a__0__c"

    def test_bad_list_value(self):
        with pytest.raises(DataError) as de:
            resolve_string_key({"a": [{"b": "c"}], "d": "e"}, "a__1__c")
        assert de.value.error == "Unmatched key a__1"

    def test_partial_id_key(self):
        assert resolve_string_key(
            {"a": [{"id": "deadbeef", "d": "e"}]}, "a__deadb__d"
        ) == ("e", ("a", 0, "d"))

    def test_invalid_partial_id_key(self):
        with pytest.raises(DataError) as de:
            resolve_string_key(
                {"a": [{"id": "deadbeef", "d": "e"}]}, "a__dead__d"
            )
        assert de.value.error == "Unmatched key a__dead"


class TestCheckStringKey(object):
    def test_list_child(self):
        assert (
            check_string_key({"a": [{"b": "c"}], "d": "e"}, "a", [{"b": "c"}])
            == []
        )

    def test_string_child(self):
        assert check_string_key({"a": [{"b": "c"}], "d": "e"}, "d", "e") == []

    def test_all_wrong(self):
        assert check_string_key(
            {"t": {"a": [{"b": "c"}], "d": "e"}},
            "t",
            {"q": [{"b": "c"}], "a": [{"z": "x"}], "r": "e"},
        ) == [
            ("t", "a", 0, "z"),
            (
                "t",
                "q",
            ),
            (
                "t",
                "r",
            ),
        ]

    def test_child(self):
        assert check_string_key(
            {"a": [{"b": "c"}], "d": "e"}, "a__0__b", "z"
        ) == [("a", 0, "b")]

    def test_list_expected(self):
        assert check_string_key(
            {"a": [{"b": []}], "d": "e"}, "a__0__b", {}
        ) == [("a", 0, "b")]

    def test_dict_expected(self):
        assert check_string_key(
            {"a": [{"b": []}], "d": "e"}, "a__0", ["b"]
        ) == [("a", 0)]


class TestFilterGlobMatch(object):
    def test_remove_leaves(self):
        data = {"q": [{"b": "c"}, {"z": "x"}], "r": "e"}
        filter_glob_match(data, ["q__0__b", "q__1__z", "r"])
        assert data == {"q": [{}, {}]}

    def test_remove_list_item(self):
        data = {"q": [{"b": "c"}, {"z": "x"}], "r": "e"}
        filter_glob_match(data, ["q__0"])
        assert data == {"q": [{"z": "x"}], "r": "e"}

    def test_protect_list_item(self):
        data = {"q": [{"b": "c"}, {"z": "x"}], "r": "e"}
        filter_glob_match(data, ["+q__1", "q__*"])
        assert data == {"q": [{"z": "x"}], "r": "e"}

    def test_protect_dict_key(self):
        data = {"q": [{"b": "c"}, {"z": "x"}], "r": "e"}
        filter_glob_match(data, ["+q", "*"])
        assert data == {"q": [{"b": "c"}, {"z": "x"}]}

    def test_del_protect_del_dict(self):
        data = {"q": "b", "c": "z", "r": "e"}
        filter_glob_match(data, ["q", "+*", "r"])
        assert data == {"c": "z", "r": "e"}

    def test_del_protect_del_list(self):
        data = [{"id": "hello"}, {"id": "world"}, {"id": "people"}]
        filter_glob_match(data, ["world", "+*", "hello"])
        assert data == [{"id": "hello"}, {"id": "people"}]


class TestMergeDict(object):
    def test_deep(self):
        data = {"a": [{"b": "c"}], "d": "e"}
        update_merge_dict(
            data, {"q": [{"b": "c"}], "a": [{"z": "x"}], "r": "e"}
        )
        assert data == {
            "q": [{"b": "c"}],
            "a": [{"b": "c", "z": "x"}],
            "r": "e",
            "d": "e",
        }

    def test_replace_child(self):
        data = {"a": [{"b": "c"}], "d": "e"}
        update_merge_dict(data, {"a": [{"b": "z"}]})
        assert data == {"a": [{"b": "z"}], "d": "e"}

    def test_replace_parent(self):
        data = {"a": [{"b": "c"}], "d": "e"}
        update_merge_dict(data, {"d": "d"})
        assert data == {"a": [{"b": "c"}], "d": "d"}

    def test_simple_list(self):
        data = {"a": ["q", "w", "e", "r", "t"]}
        update_merge_dict(data, {"a": ["z", "x", "c"]})
        assert data == {"a": ["z", "x", "c", "r", "t"]}

    def test_list_expected(self):
        data = {"a": [{"b": []}], "d": "e"}
        with pytest.raises(DataError) as de:
            update_merge_dict(data, {"a": [{"b": {}}]})
        assert de.value.error == "Expected list for a__0__b"

    def test_dict_expected(self):
        data = {"a": [{"b": []}], "d": "e"}
        with pytest.raises(DataError) as de:
            update_merge_dict(data, {"a": [["b"]]})
        assert de.value.error == "Expected dict for a__0"


class TestMergeStringKey(object):
    def test_replace_child(self):
        data = {"a": [{"b": "c"}], "d": "e"}
        update_merge_string_key(data, "a__0__b", "z")
        assert data == {"a": [{"b": "z"}], "d": "e"}

    def test_replace_parent(self):
        data = {"a": [{"b": "c"}], "d": "e"}
        update_merge_string_key(data, "d", "d")
        assert data == {"a": [{"b": "c"}], "d": "d"}

    def test_simple_list(self):
        data = {"a": ["q", "w", "e", "r", "t"]}
        update_merge_string_key(data, "a__0", "z")
        assert data == {"a": ["z", "w", "e", "r", "t"]}

    def test_list_expected(self):
        data = {"a": [{"b": []}], "d": "e"}
        with pytest.raises(DataError) as de:
            update_merge_string_key(data, "a__0__b", {})
        assert de.value.error == "Expected list for a__0__b"

    def test_dict_expected(self):
        data = {"a": [{"b": []}], "d": "e"}
        with pytest.raises(DataError) as de:
            update_merge_string_key(data, "a__0", ["b"])
        assert de.value.error == "Expected dict for a__0"


schema = {
    "__after": [identity_converter],
    "__extra": [identity_converter],
    "__junk": [identity_converter],
    "0": [identity_converter],
    "1": [identity_converter],
    "2": {
        "__before": [identity_converter],
        "__after": [identity_converter],
        "20": [identity_converter],
        "22": [identity_converter],
        "21": {"210": [identity_converter]},
    },
    "3": {"30": [identity_converter]},
}

data = {
    ("0",): "0 value",
    # key 1 missing
    ("2", 0, "20"): "20 value 0",
    # key 2,22 missing
    ("2", 0, "21", 0, "210"): "210 value 0,0",
    # key 3 missing subdict
    ("2", 1, "20"): "20 value 1",
    ("2", 1, "22"): "22 value 1",
    ("2", 1, "21", 0, "210"): "210 value 1,0",
    ("2", 1, "21", 1, "210"): "210 value 1,1",
    ("2", 1, "21", 3, "210"): "210 value 1,3",  # out of order sequence
    ("4", 1, "30"): "30 value 1",  # junk key as no 4 and no subdict
    ("4",): "4 value",  # extra key 4
    #    ("2", 2, "21", 0, "210"): "210 value 2,0" #junk key as it does not have a parent
}


class TestDictization:
    def test_flatten_schema(self):

        flattened_schema = flatten_schema(schema)

        assert flattened_schema == {
            ("0",): [identity_converter],
            ("1",): [identity_converter],
            ("2", "20"): [identity_converter],
            ("2", "__after"): [identity_converter],
            ("2", "__before"): [identity_converter],
            ("2", "21", "210"): [identity_converter],
            ("2", "22"): [identity_converter],
            ("3", "30"): [identity_converter],
            ("__after",): [identity_converter],
            ("__extra",): [identity_converter],
            ("__junk",): [identity_converter],
        }

    def test_get_key_combination(self):

        flattened_schema = flatten_schema(schema)
        assert get_all_key_combinations(data, flattened_schema) == set(
            [
                (),
                ("2", 0),
                ("2", 1),
                ("2", 1, "21", 0),
                ("2", 0, "21", 0),
                ("2", 1, "21", 1),
                ("2", 1, "21", 3),
            ]
        ), get_all_key_combinations(data, flattened_schema)

        # state = {}
        # make_flattened_schema(data, schema, state)

    def test_make_full_schema(self):

        full_schema = make_full_schema(data, schema)

        assert set(full_schema.keys()) - set(data.keys()) == set(
            [
                ("2", 1, "__before"),
                ("2", 0, "__after"),
                ("2", 0, "22"),
                ("1",),
                ("2", 1, "__after"),
                ("2", 0, "__before"),
                ("__after",),
                ("__extra",),
                ("__junk",),
            ]
        )

        assert set(data.keys()) - set(full_schema.keys()) == set(
            [("4",), ("4", 1, "30")]
        )

    def test_augment_junk_and_extras(self):

        assert augment_data(data, schema) == {
            ("__junk",): {("4", 1, "30"): "30 value 1"},
            ("0",): "0 value",
            ("1",): missing,
            ("2", 0, "20"): "20 value 0",
            ("2", 0, "21", 0, "210"): "210 value 0,0",
            ("2", 0, "22"): missing,
            ("2", 1, "20"): "20 value 1",
            ("2", 1, "21", 0, "210"): "210 value 1,0",
            ("2", 1, "21", 1, "210"): "210 value 1,1",
            ("2", 1, "21", 3, "210"): "210 value 1,3",
            ("2", 1, "22"): "22 value 1",
            ("__extras",): {"4": "4 value"},
        }

    def test_identity_validation(self):

        converted_data, errors = validate_flattened(data, schema)

        assert not errors

        assert sorted(converted_data) == sorted(
            {
                ("__junk",): {
                    ("2", 2, "21", 0, "210"): "210 value 2,0",
                    ("4", 1, "30"): "30 value 1",
                },
                ("0",): "0 value",
                ("1",): missing,
                ("2", 0, "20"): "20 value 0",
                ("2", 0, "21", 0, "210"): "210 value 0,0",
                ("2", 0, "22"): missing,
                ("2", 1, "20"): "20 value 1",
                ("2", 1, "21", 0, "210"): "210 value 1,0",
                ("2", 1, "21", 1, "210"): "210 value 1,1",
                ("2", 1, "21", 3, "210"): "210 value 1,3",
                ("2", 1, "22"): "22 value 1",
                ("__extras",): {"4": "4 value"},
            }
        ), pformat(sorted(converted_data))

    def test_basic_errors(self):
        schema = {
            "__junk": [empty],
            "__extras": [empty],
            "0": [identity_converter],
            "1": [not_empty],
            "2": {
                "__before": [identity_converter],
                "__after": [identity_converter],
                "20": [identity_converter],
                "22": [identity_converter],
                "__extras": [empty],
                "21": {"210": [identity_converter]},
            },
            "3": {"30": [identity_converter]},
        }

        converted_data, errors = validate_flattened(data, schema)

        assert errors == {
            ("__junk",): [
                u"The input field [('4', 1, '30')] was not expected."
            ],
            ("1",): [u"Missing value"],
            ("__extras",): [u"The input field __extras was not expected."],
        }, errors

    def test_flatten(self):

        data = {
            "extras": [
                {"key": "genre", "value": u"horror"},
                {"key": "media", "value": u"dvd"},
            ],
            "license_id": u"gpl-3.0",
            "name": u"testpkg",
            "resources": [
                {
                    u"alt_url": u"alt_url",
                    u"description": u"Second file",
                    u"extras": {u"size": u"200"},
                    u"format": u"xml",
                    u"hash": u"def123",
                    u"url": u"http://blah.com/file2.xml",
                },
                {
                    u"alt_url": u"alt_url",
                    u"description": u"Main file",
                    u"extras": {u"size": u"200"},
                    u"format": u"xml",
                    u"hash": u"abc123",
                    u"url": u"http://blah.com/file.xml",
                },
            ],
            "tags": [{"name": u"russion"}, {"name": u"novel"}],
            "title": u"Some Title",
            "url": u"http://blahblahblah.mydomain",
        }

        assert flatten_dict(data) == {
            ("extras", 0, "key"): "genre",
            ("extras", 0, "value"): u"horror",
            ("extras", 1, "key"): "media",
            ("extras", 1, "value"): u"dvd",
            ("license_id",): u"gpl-3.0",
            ("name",): u"testpkg",
            ("resources", 0, u"alt_url"): u"alt_url",
            ("resources", 0, u"description"): u"Second file",
            ("resources", 0, u"extras"): {u"size": u"200"},
            ("resources", 0, u"format"): u"xml",
            ("resources", 0, u"hash"): u"def123",
            ("resources", 0, u"url"): u"http://blah.com/file2.xml",
            ("resources", 1, u"alt_url"): u"alt_url",
            ("resources", 1, u"description"): u"Main file",
            ("resources", 1, u"extras"): {u"size": u"200"},
            ("resources", 1, u"format"): u"xml",
            ("resources", 1, u"hash"): u"abc123",
            ("resources", 1, u"url"): u"http://blah.com/file.xml",
            ("tags", 0, "name"): u"russion",
            ("tags", 1, "name"): u"novel",
            ("title",): u"Some Title",
            ("url",): u"http://blahblahblah.mydomain",
        }, pformat(flatten_dict(data))

        assert data == unflatten(flatten_dict(data))

    def test_flatten_deeper(self):
        data = {
            u"resources": [
                {
                    u"subfields": [
                        {
                            u"test": u"hello",
                        },
                    ],
                },
            ],
        }

        assert flatten_dict(data) == {
            ("resources", 0, u"subfields", 0, u"test"): u"hello",
        }, pformat(flatten_dict(data))

        assert data == unflatten(flatten_dict(data)), pformat(
            unflatten(flatten_dict(data))
        )

    def test_unflatten_regression(self):
        fdata = {
            (u"items", 0, u"name"): u"first",
            (u"items", 0, u"value"): u"v1",
            (u"items", 3, u"name"): u"second",
            (u"items", 3, u"value"): u"v2",
        }
        expected = {
            u"items": [
                {u"name": u"first", u"value": u"v1"},
                {u"name": u"second", u"value": u"v2"},
            ],
        }
        assert unflatten(fdata) == expected, pformat(unflatten(fdata))

    def test_simple(self):
        schema = {
            "name": [not_empty],
            "age": [ignore_missing, convert_int],
            "gender": [default("female")],
        }

        data = {"name": "fred", "age": "32"}

        converted_data, errors = validate(data, schema)

        assert not errors
        assert converted_data == {
            "gender": "female",
            "age": 32,
            "name": "fred",
        }, converted_data

        data = {"name": "", "age": "dsa32", "extra": "extra"}

        converted_data, errors = validate(data, schema)

        assert errors == {
            "age": [u"Please enter an integer value"],
            "name": [u"Missing value"],
        }, errors

        assert converted_data == {
            "gender": "female",
            "age": "dsa32",
            "name": "",
            "__extras": {"extra": "extra"},
        }

        data = {
            "name": "fred",
            "numbers": [
                {"number": "13221312"},
                {"number": "432423432", "code": "+44"},
            ],
        }

        schema = {
            "name": [not_empty],
            "numbers": {
                "number": [convert_int],
                "code": [not_empty],
                "__extras": [ignore],
            },
        }

        converted_data, errors = validate(data, schema)

        assert errors == {"numbers": [{"code": [u"Missing value"]}, {}]}

    def test_error_list_position(self):
        data = {
            "name": "fred",
            "cats": [{"name": "rita"}, {"name": "otis"}],
            "numbers": [
                {"number": "432423432", "code": "+44"},
                {"number": "13221312"},
                {"number": "432423432", "code": "+44"},
                {"number": "13221312"},
                {"number": "432423432", "code": "+44"},
            ],
        }

        schema = {
            "name": [not_empty],
            "cats": {
                "name": [not_empty],
            },
            "numbers": {
                "number": [convert_int],
                "code": [not_empty],
                "__extras": [ignore],
            },
        }

        converted_data, errors = validate(data, schema)

        assert errors == {
            "numbers": [
                {},
                {"code": [u"Missing value"]},
                {},
                {"code": [u"Missing value"]},
                {},
            ]
        }

    def test_simple_converter_types(self):
        schema = {
            "name": [not_empty, unicode_safe],
            "age": [ignore_missing, convert_int],
            "gender": [default("female")],
        }

        data = {"name": "fred", "age": "32"}

        converted_data, errors = validate(data, schema)
        assert not errors
        assert converted_data == {
            "gender": "female",
            "age": 32,
            "name": u"fred",
        }, converted_data

        assert isinstance(converted_data["name"], str)
        assert isinstance(converted_data["gender"], str)


def validate_flattened(data, schema, context=None):

    context = context or {}
    assert isinstance(data, dict)
    converted_data, errors = _validate(data, schema, context)

    for key, value in list(errors.items()):
        if not value:
            errors.pop(key)

    return converted_data, errors
