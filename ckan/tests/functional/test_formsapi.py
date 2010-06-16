from pylons import config
import webhelpers
import re

from ckan.tests import *
import ckan.model as model
import ckan.authz as authz
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.helpers import json

ACCESS_DENIED = [403]

class BaseFormsApiCase(TestController):

    api_version = ''
    package_name = u'formsapi'
    package_name_alt = u'formsapialt'

    def get(self, *args, **kwds):
        offset = url_for(*args, **kwds)
        res = self.app.get(offset)
        return res

    def submit(self, form_data={}, form=None, res=None, forms_index=0, button_name='send', *args, **kwds):
        if not form:
            if not res:
                res = self.get(*args, **kwds)
            form = res.forms[forms_index]
        for (name, value) in form_data.items():
            if type(value) == unicode:
                value = value.encode('utf8')
            form[name] = value
        #headers = self.write_cookie_headers()
        res = form.submit(button_name)#, headers=headers)
        #self.read_cookie_headers(res)
        #res = self.try_to_follow(res)
        return res

    def get_package_edit_form(self, package_id):
        return self.get(controller='formsapi', action='package_edit', id=package_id)

    def submit_package_edit_form(self, package_id, **kwds):
        return self.submit(form_data=kwds, controller='formsapi', action='package_edit', id=package_id)

    def create_package_fixture(self, **kwds):
        self.create_package(name=self.package_name)
        

class TestFormsApi(BaseFormsApiCase):

    api_version = '1'

    def teardown(self):
        self.purge_package_by_name(self.package_name)
        self.purge_package_by_name(self.package_name_alt)

    def test_get_package_edit_form(self):
        self.create_package_fixture()
        package = self.get_package_by_name(self.package_name)
        res = self.get_package_edit_form(package.id)
        assert '<html>' not in res, res
        assert '<form>' not in res, res
        assert '<fieldset>' in res, res
        assert package.name in res, res

    def test_submit_package_edit_form_valid(self):
        package = self.get_package_by_name(self.package_name)
        res = self.submit_package_edit_form(name=self.package_name_alt)
        assert 'form' in res

    def test_submit_package_edit_form_errors(self):
        res = self.submit_package_edit_form()
        assert 'form' in res
        assert 'errors' in res


