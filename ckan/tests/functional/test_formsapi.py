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

    def setup(self):
        self.user = self.create_user(name=u'alex')
        self.extra_environ = {
            'Authorization' : str(self.user.apikey)
        }
        self.create_package(name=self.package_name)

    def teardown(self):
        if self.user:
            model.Session.remove()
            model.Session.add(self.user)
            self.user.purge()
        self.purge_package_by_name(self.package_name)
        self.purge_package_by_name(self.package_name_alt)

    def get(self, status=[200], *args, **kwds):
        offset = url_for(*args, **kwds)
        res = self.app.get(offset, status=status, extra_environ=self.extra_environ)
        return res

    def post(self, data, status=[200], *args, **kwds):
        offset = url_for(*args, **kwds)
        params = '%s=1' % json.dumps(data)
        res = self.app.post(offset, params=params, status=status, extra_environ=self.extra_environ)
        return res

    def get_package_edit_form(self, package_id, status=[200]):
        return self.get(controller='formsapi', action='package_edit', id=package_id, status=status)

    def post_package_edit_form(self, package_id, status=[200], **kwds):
        res = self.get_package_edit_form(package_id)
        res.body = "<html><form action=\"\" method=\"post\">" + res.body + "<input type=\"submit\" name=\"send\"></form></html>"
        form = res.forms[0]
        for key,value in kwds.items():
            field_name = 'Package-%s-%s' % (package_id, key)
            form[field_name] = value
        form_data = form.submit_fields()
        departments = ['department1', 'department2', 'department3']
        request_data = {
            'form_data': form_data,
            'choices': {'departments': departments},
        }
        return self.post(request_data, controller='formsapi', action='package_edit', status=status)
        
    def assert_not_header(self, res, name):
        keys = self.get_header_keys(res)
        assert not name in keys, res

    def assert_header(self, res, name):
        keys = self.get_header_keys(res)
        assert name in keys, res

    def get_header_keys(self, res):
        return [h[0] for h in res.headers]



class TestFormsApi(BaseFormsApiCase):

    api_version = '1'

    def test_get_package_edit_form(self):
        package = self.get_package_by_name(self.package_name)
        res = self.get_package_edit_form(package.id)
        assert '<fieldset>' in res, res
        assert package.name in res, res

    def test_submit_package_edit_form_valid(self):
        package = self.get_package_by_name(self.package_name)
        res = self.post_package_edit_form(package.id, name=self.package_name_alt)
        self.assert_header(res, 'Location')
        assert not self.get_package_by_name(self.package_name)
        assert self.get_package_by_name(self.package_name_alt)

    def test_submit_package_edit_form_errors(self):
        package = self.get_package_by_name(self.package_name)
        invalid_name = ''
        res = self.post_package_edit_form(package.id, name=invalid_name)
        self.assert_not_header(res, 'Location')
        assert self.get_package_by_name(self.package_name)
        invalid_name = ' '
        self.post_package_edit_form(package.id, name=invalid_name)
        self.assert_not_header(res, 'Location')
        assert self.get_package_by_name(self.package_name)

