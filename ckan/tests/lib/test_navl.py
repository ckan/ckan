# encoding: utf-8

import nose
import pylons

from ckan.tests import helpers
from ckan.config import environment

eq_ = nose.tools.eq_


class TestFormencdoeLanguage(object):
    @helpers.change_config('ckan.locale_default', 'de')
    def test_formencode_uses_locale_default(self):
        environment.update_config()
        from ckan.lib.navl.dictization_functions import validate
        from ckan.lib.navl.validators import not_empty
        from formencode import validators
        schema = {
            "name": [not_empty, unicode],
            "email": [validators.Email],
            "email2": [validators.Email],
        }

        data = {
            "name": "fred",
            "email": "32",
            "email2": "david@david.com",
        }

        converted_data, errors = validate(data, schema)
        eq_({'email': [u'Eine E-Mail-Adresse muss genau ein @-Zeichen enthalten']}, errors)
