# encoding: utf-8

import pytest

from ckan.logic import UnknownValidator
from ckan.plugins.toolkit import get_validator, Invalid
from ckan import plugins


@pytest.mark.ckan_config("ckan.plugins", "example_ivalidators")
@pytest.mark.usefixtures("with_plugins")
class TestIValidators:
    def test_custom_validator_validates(self):
        v = get_validator("equals_fortytwo")
        with pytest.raises(Invalid):
            v(41)

    def test_custom_validator_passes(self):
        v = get_validator("equals_fortytwo")
        assert v(42) == 42

    def test_custom_converter_converts(self):
        c = get_validator("negate")
        assert c(19) == -19

    def test_overridden_validator(self):
        v = get_validator("unicode_only")
        assert u"Hola cómo estás" == v("Hola c\xf3mo est\xe1s")


@pytest.mark.usefixtures("with_plugins")
class TestNoIValidators(object):
    def test_no_overridden_validator(self):
        v = get_validator("unicode_only")
        with pytest.raises(Invalid):
            v(b"Hola c\xf3mo est\xe1s")


@pytest.mark.ckan_config("example.ivalidators.number", "10")
@pytest.mark.usefixtures("with_plugins")
def test_validator_used_by_declaration(ckan_config):
    assert ckan_config["example.ivalidators.number"] == "10"

    with pytest.raises(UnknownValidator):
        # call get_validator with any value to build validators cache. Without
        # this line, the test has no sense, because custom validators are
        # blocked exactly by existing cache.
        get_validator("negate")

    plugins.load("example_ivalidators")

    try:
        assert ckan_config["example.ivalidators.number"] == -10
    finally:
        plugins.unload("example_ivalidators")
