from nose.tools import assert_equals, assert_raises
import pylons.config as config

from ckan.plugins.toolkit import get_validator, Invalid
from ckan import plugins


class TestIValidators(object):
    @classmethod
    def setup_class(cls):
        plugins.load('example_ivalidators')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_ivalidators')

    def test_custom_validator_validates(self):
        v = get_validator('equals_fortytwo')
        assert_raises(Invalid, v, 41)

    def test_custom_validator_passes(self):
        v = get_validator('equals_fortytwo')
        assert_equals(v(42), 42)

    def test_custom_converter_converts(self):
        c = get_validator('negate')
        assert_equals(c(19), -19)
