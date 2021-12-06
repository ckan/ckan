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
        assert option._normalize(option.default) == 123
        assert option._normalize("10") == 10
        assert option._normalize(50) == 50

        option.set_default("yes").set_validators("boolean_validator")
        assert option._normalize(option.default) is True
        assert option._normalize("no") is False
        assert option._normalize(False) is False
