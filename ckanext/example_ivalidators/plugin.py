# encoding: utf-8

import six
from six import text_type

from ckan.plugins.toolkit import Invalid
from ckan import plugins


class ExampleIValidatorsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self):
        return {
            'equals_fortytwo': equals_fortytwo,
            'negate': negate,
            'unicode_only': unicode_please,
        }


def equals_fortytwo(value):
    if value != 42:
        raise Invalid('not 42')
    return value


def negate(value):
    return -value


def unicode_please(value):
    if isinstance(value, six.binary_type):
        try:
            return six.ensure_text(value)
        except UnicodeDecodeError:
            return value.decode('cp1252')
    return text_type(value)
