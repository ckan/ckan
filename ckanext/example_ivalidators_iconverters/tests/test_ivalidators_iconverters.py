from nose.tools import assert_equals, assert_raises
import pylons.config as config

from ckan.plugins import toolkit
from ckan import plugins


class TestIValidators(object):
    @classmethod
    def setup_class(cls):
        plugins.load('example_ivalidators')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_ivalidators')

    def test_custom_validator_validates(self):
        v = toolkit.get_validator('equals_fortytwo')
        assert_raises(toolkit.Invalid, v, 41)

    def test_custom_validator_passes(self):
        v = toolkit.get_validator('equals_fortytwo')
        assert_equals(v(42), 42)


class TestIConverters(object):
    @classmethod
    def setup_class(cls):
        plugins.load('example_iconverters')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iconverters')

    def test_custom_converter_converts(self):
        c = toolkit.get_converter('negate')
        assert_equals(c(19), -19)

