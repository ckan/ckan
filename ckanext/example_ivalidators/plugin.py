# encoding: utf-8

from six import text_type

from ckan.plugins.toolkit import Invalid
from ckan import plugins


class ExampleIValidatorsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self):
        return {
            u'equals_fortytwo': equals_fortytwo,
            u'negate': negate,
            u'unicode_only': unicode_please,
        }


def equals_fortytwo(value):
    if value != 42:
        raise Invalid(u'not 42')
    return value


def negate(value):
    return -value


def unicode_please(value):
    if isinstance(value, bytes):
        try:
            return value.decode(u'utf8')
        except UnicodeDecodeError:
            return value.decode(u'cp1252')
    return text_type(value)
