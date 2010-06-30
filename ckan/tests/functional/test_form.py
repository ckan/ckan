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
        self.user = self.get_user_by_name(u'tester')
        if not self.user:
            self.user = self.create_user(name=u'tester')
        self.extra_environ = {
            'Authorization' : str(self.user.apikey)
        }
        self.create_package(name=self.package_name)

    def teardown(self):
        #if self.user:
        #    model.Session.remove()
        #    model.Session.add(self.user)
        #    self.user.purge()
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
        res = self.get(controller='form', action='package_edit', id=package_id, status=status)
        form = self.form_from_res(res)
        return form

    def form_from_res(self, res):
        assert not "<html>" in str(res.body), "The response is an HTML doc, not just a form: %s" % str(res.body)
        res.body = "<html><form action=\"\" method=\"post\">" + res.body + "<input type=\"submit\" name=\"send\"></form></html>"
        form = res.forms[0]
        return form

    def post_package_edit_form(self, package_id, form=None, status=[200], **kwds):
        if form == None:
            form = self.get_package_edit_form(package_id)
        for key,value in kwds.items():
            field_name = 'Package-%s-%s' % (package_id, key)
            form[field_name] = value
        form_data = form.submit_fields()
        request_data = {
            'form_data': form_data,
            'log_message': 'Unit-testing the Forms API...',
            'author': 'automated test suite',
        }
        return self.post(request_data, controller='form', action='package_edit', id=package_id, status=status)
        
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
        form = self.get_package_edit_form(package.id)
        field_name = 'Package-%s-name' % (package.id)
        field_value = form[field_name].value
        self.assert_equal(field_value, package.name)

    def test_submit_package_edit_form_valid(self):
        package = self.get_package_by_name(self.package_name)
        res = self.post_package_edit_form(package.id, name=self.package_name_alt)
        self.assert_header(res, 'Location')
        assert not json.loads(res.body)
        assert not self.get_package_by_name(self.package_name)
        assert self.get_package_by_name(self.package_name_alt)

    def test_submit_package_edit_form_errors(self):
        package = self.get_package_by_name(self.package_name)
        package_id = package.id
        # Nothing in name.
        invalid_name = ''
        res = self.post_package_edit_form(package_id, name=invalid_name, status=[400])
        # Check location header is not set.
        self.assert_not_header(res, 'Location')
        # Check package is unchanged.
        assert self.get_package_by_name(self.package_name)
        # Check response is an error form.
        assert "class=\"field_error\"" in res
        form = self.form_from_res(res)
        field_name = 'Package-%s-name' % (package_id)
        field_value = form[field_name].value
        assert field_value == invalid_name, (field_value, invalid_name)

        # Whitespace in name.
        invalid_name = ' '
        res = self.post_package_edit_form(package_id, name=invalid_name, status=[400])
        # Check location header is not set.
        self.assert_not_header(res, 'Location')
        # Check package is unchanged.
        assert self.get_package_by_name(self.package_name)
        # Check response is an error form.
        assert "class=\"field_error\"" in res
        form = self.form_from_res(res)
        field_name = 'Package-%s-name' % (package_id)
        field_value = form[field_name].value
        assert field_value == invalid_name, (field_value, invalid_name)
        # Check submitting error form with corrected values is OK.
        res = self.post_package_edit_form(package_id, form=form, name=self.package_name_alt)
        self.assert_header(res, 'Location')
        assert not json.loads(res.body)
        assert not self.get_package_by_name(self.package_name)
        assert self.get_package_by_name(self.package_name_alt)

    def test_package_edit_example_page(self):
        self.ckan_server = self._start_ckan_server()
        try:
            self._wait_for_url('http://127.0.0.1:5000')
            package = self.get_package_by_name(self.package_name)
            package_id = package.id
            res = self.get(controller='form', action='package_edit_example', id=package_id)
            form = res.forms[0]
            form_data = form.submit_fields()
            import urllib
            params = urllib.urlencode(form_data)
            offset = url_for(controller='form', action='package_edit_example', id=package_id)
            res = self.app.post(offset, params=params, status=[200], extra_environ=self.extra_environ)
            body = res.body
            assert '<html' in body, "The result does NOT have an HTML doc tag: %s" % body
            assert "Submitted OK" in body, body
        finally:
            self._stop_ckan_server(self.ckan_server)

