# encoding: utf-8

import pytest
import six
from six import text_type
from ckan.lib.navl.dictization_functions import validate, Invalid


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
