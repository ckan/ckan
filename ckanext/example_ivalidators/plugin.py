# encoding: utf-8

from __future__ import annotations

from typing import Any
from ckan.types import Validator


from ckan.plugins.toolkit import Invalid, blanket
from ckan import plugins


@blanket.config_declarations
class ExampleIValidatorsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self) -> dict[str, Validator]:
        return {
            u'equals_fortytwo': equals_fortytwo,
            u'negate': negate,
            u'unicode_only': unicode_please,
        }


def equals_fortytwo(value: Any):
    if value != 42:
        raise Invalid(u'not 42')
    return value


def negate(value: Any):
    return -value


def unicode_please(value: Any):
    if isinstance(value, bytes):
        try:
            return str(value)
        except UnicodeDecodeError:
            return value.decode(u'cp1252')
    return str(value)
