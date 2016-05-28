# encoding: utf-8

from ckan.plugins.toolkit import Invalid
from ckan import plugins


class ExampleIValidatorsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self):
        return {
            'equals_fortytwo': equals_fortytwo,
            'negate': negate,
            }


def equals_fortytwo(value):
    if value != 42:
        raise Invalid('not 42')
    return value


def negate(value):
    return -value
