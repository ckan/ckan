# -*- coding: utf-8 -*-

from ckan.config.declaration import Option


class TestDetails:
    def test_default_value(self):
        assert Option("def").has_default()
        assert Option("").has_default()
        assert Option(False).has_default()

        assert not Option(None).has_default()
        assert not Option().has_default()

    def test_normalize(self):
        option = Option("123")
        option.set_validators("int_validator")
        assert option.normalize(option.default) == 123
        assert option.normalize("10") == 10
        assert option.normalize(50) == 50

        option.set_default("yes").set_validators("boolean_validator")
        assert option.normalize(option.default) is True
        assert option.normalize("no") is False
        assert option.normalize(False) is False

        option.set_default("")
        option.set_validators("default(xxx)")
        assert option.normalize(option.default) == "xxx"

        option.set_validators("default('yyy')")
        assert option.normalize(option.default) == "yyy"

        option.set_validators("default(10)")
        assert option.normalize(option.default) == 10

        option.set_validators("default('10')")
        assert option.normalize(option.default) == "10"

        option.set_validators("default([[],{():None}])")
        assert option.normalize(option.default) == [[], {(): None}]

    def test_str_value(self):
        option = Option()
        assert option.str_value() == ""
        assert option.str_value(1) == "1"
        assert option.str_value([1, 2]) == "[1, 2]"

        option = Option().set_validators("as_list")
        assert option.str_value() == ""
        assert option.str_value(1) == "1"
        assert option.str_value([1, 2]) == "1 2"

        option = Option([10, 20]).set_validators("as_list")
        assert option.str_value() == "10 20"
        assert option.str_value(1) == "1"
        assert option.str_value([1, 2]) == "1 2"
