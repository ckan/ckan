from pylons import config
import webhelpers
import re

from ckan.tests import *
import ckan.model as model
import ckan.authz as authz
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.helpers import json

ACCESS_DENIED = [403]

# Todo: Test for access control setup. Just checking an object exists in the model doesn't mean it will be presented through the WebUI.

from ckan.tests.functional.api.test_model import ApiControllerTestCase
from ckan.tests.functional.api.test_model import Api1TestCase
from ckan.tests.functional.api.test_model import Api2TestCase
from ckan.tests.functional.api.test_model import ApiUnversionedTestCase

class BaseFormsApiCase(ModelMethods, ApiControllerTestCase):

    api_version = ''
    package_name = u'formsapi'
    package_name_alt = u'formsapialt'
    package_name_alt2 = u'formsapialt2'
    apikey_header_name = config.get('apikey_header_name', 'X-CKAN-API-Key')

    def setup(self):
        self.user = self.get_user_by_name(u'tester')
        if not self.user:
            self.user = self.create_user(name=u'tester')
        self.extra_environ = {
            self.apikey_header_name : str(self.user.apikey)
        }
        self.create_package(name=self.package_name)
        self.harvest_source = None

    def teardown(self):
        #if self.user:
        #    model.Session.remove()
        #    model.Session.add(self.user)
        #    self.user.purge()
        self.purge_package_by_name(self.package_name)
        self.purge_package_by_name(self.package_name_alt)
        self.purge_package_by_name(self.package_name_alt2)
        self.delete_harvest_source(u'http://localhost/')
        if self.harvest_source:
            self.delete_commit(self.harvest_source)

    def delete_harvest_source(self, url):
        source = self.get_harvest_source_by_url(url, None)
        if source:
            self.delete_commit(source)

    def offset_package_create_form(self):
        return self.offset('/form/package/create')

    def offset_package_edit_form(self, ref):
        return self.offset('/form/package/edit/%s' % ref)

    def offset_harvest_source_create_form(self):
        return self.offset('/form/harvestsource/create')

    def offset_harvest_source_edit_form(self, ref):
        return self.offset('/form/harvestsource/edit/%s' % ref)

    def get_package_create_form(self, status=[200]):
        offset = self.offset_package_create_form()
        res = self.get(offset, status=status)
        return self.form_from_res(res)

    def get_package_edit_form(self, package_ref, status=[200]):
        offset = self.offset_package_edit_form(package_ref)
        res = self.get(offset, status=status)
        return self.form_from_res(res)

    def get_harvest_source_create_form(self, status=[200]):
        offset = self.offset_harvest_source_create_form()
        res = self.get(offset, status=status)
        return self.form_from_res(res)

    def get_harvest_source_edit_form(self, harvest_source_id, status=[200]):
        offset = self.offset_harvest_source_edit_form(harvest_source_id)
        res = self.get(offset, status=status)
        return self.form_from_res(res)

    def form_from_res(self, res):
        assert not "<html>" in str(res.body), "The response is an HTML doc, not just a form: %s" % str(res.body)
        # Arrange 'form fixture' from fieldsets string (helps testing Form API).
        res.body = "<html><form id=\"test\" action=\"\" method=\"post\">" + res.body + "<input type=\"submit\" name=\"send\"></form></html>"
        return res.forms['test']

    def post_package_create_form(self, form=None, status=[201], **kwds):
        if form == None:
            form = self.get_package_create_form()
        for key,field_value in kwds.items():
            field_name = 'Package--%s' % key
            form[field_name] = field_value
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'log_message': 'Unit-testing the Forms API...',
            'author': 'automated test suite',
        }
        offset = self.offset_package_create_form()
        return self.post(offset, data, status=status)

    def post_harvest_source_create_form(self, form=None, status=[201], **kwds):
        if form == None:
            form = self.get_harvest_source_create_form()
        for key,field_value in kwds.items():
            field_name = 'HarvestSource--%s' % key
            form[field_name] = field_value
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'user_ref': 'example publisher user',
            'publisher_ref': 'example publisher',
        }
        offset = self.offset_harvest_source_create_form()
        return self.post(offset, data, status=status)

    def package_id_from_ref(self, package_ref):
        if self.ref_package_by == 'id':
            return package_ref
        elif self.ref_package_by == 'name':
            package = model.Package.get(package_ref)
            return package.id
        else:
            raise Exception, "Unsupported value for ref_package_by: %s" % self.ref_package_by

    def post_package_edit_form(self, package_ref, form=None, status=[200], **kwds):
        if form == None:
            form = self.get_package_edit_form(package_ref)
        for key,field_value in kwds.items():
            package_id = self.package_id_from_ref(package_ref)
            field_name = 'Package-%s-%s' % (package_id, key)
            self.set_formfield(form, field_name, field_value)
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'log_message': 'Unit-testing the Forms API...',
            'author': 'automated test suite',
        }
        offset = self.offset_package_edit_form(package_ref)
        return self.post(offset, data, status=status)
        
    def post_harvest_source_edit_form(self, harvest_source_id, form=None, status=[200], **kwds):
        if form == None:
            form = self.get_harvest_source_edit_form(harvest_source_id)
        for key,field_value in kwds.items():
            field_name = 'HarvestSource-%s-%s' % (harvest_source_id, key)
            self.set_formfield(form, field_name, field_value)
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'user_ref': 'example publisher user',
            'publisher_ref': 'example publisher',
        }
        offset = self.offset_harvest_source_edit_form(harvest_source_id)
        return self.post(offset, data, status=status)
        
    def set_formfield(self, form, field_name, field_value):
        form[field_name] = field_value

    def assert_not_header(self, res, name):
        headers = self.get_headers(res)
        assert not name in headers, "Found header '%s' in response: %s" % (name, res)

    def assert_header(self, res, name, value=None):
        headers = self.get_headers(res)
        assert name in headers, "Couldn't find header '%s' in response: %s" % (name, res)
        if value != None:
            self.assert_equal(headers[name], value)

    def get_header_keys(self, res):
        return [h[0] for h in res.headers]

    def get_headers(self, res):
        headers = {}
        for h in res.headers:
            name = h[0]
            value = h[1]
            headers[name] = value
        return headers


class FormsApiTestCase(BaseFormsApiCase):

    def get_field_names(self, form):
        return form.fields.keys()

    def assert_formfield(self, form, name, expected_value):
        try:
            field_value = form[name]
        except Exception, inst:
            msg = "Couldn't read field '%s' from form fields: %s: %s" % (
                name, self.get_field_names(form), inst
            )
            raise Exception, msg 
        self.assert_equal(field_value, expected_value)

    def test_get_package_create_form(self):
        form = self.get_package_create_form()
        self.assert_formfield(form, 'Package--name', '')
        self.assert_formfield(form, 'Package--title', '')
        self.assert_formfield(form, 'Package--version', '')
        self.assert_formfield(form, 'Package--url', '')
        self.assert_formfield(form, 'Package--notes', '')
        self.assert_formfield(form, 'Package--resources-0-url', '')
        self.assert_formfield(form, 'Package--resources-0-format', '')
        self.assert_formfield(form, 'Package--resources-0-description', '')
        self.assert_formfield(form, 'Package--resources-0-hash', '')
        self.assert_formfield(form, 'Package--resources-0-id', '')
        self.assert_formfield(form, 'Package--author', '')
        self.assert_formfield(form, 'Package--author_email', '')
        self.assert_formfield(form, 'Package--maintainer', '')
        self.assert_formfield(form, 'Package--maintainer_email', '')
        self.assert_formfield(form, 'Package--license_id', '')
        self.assert_formfield(form, 'Package--extras-newfield0-key', '')
        self.assert_formfield(form, 'Package--extras-newfield0-value', '')
        self.assert_formfield(form, 'Package--extras-newfield1-key', '')
        self.assert_formfield(form, 'Package--extras-newfield1-value', '')
        self.assert_formfield(form, 'Package--extras-newfield2-key', '')
        self.assert_formfield(form, 'Package--extras-newfield2-value', '')

    def test_submit_package_create_form_valid(self):
        package_name = self.package_name_alt
        assert not self.get_package_by_name(package_name)
        res = self.post_package_create_form(name=package_name)
        self.assert_header(res, 'Location')
        assert not json.loads(res.body)
        self.assert_header(res, 'Location', 'http://localhost'+self.package_offset(package_name))

    def test_submit_package_create_form_invalid(self):
        package_name = self.package_name_alt
        assert not self.get_package_by_name(package_name)
        res = self.post_package_create_form(name='', status=[400])
        self.assert_not_header(res, 'Location')
        assert "Name: Please enter a value" in res.body
        assert not self.get_package_by_name(package_name)

    def test_get_package_edit_form(self):
        package = self.get_package_by_name(self.package_name)
        form = self.get_package_edit_form(package.id)
        field_name = 'Package-%s-name' % (package.id)
        self.assert_formfield(form, field_name, package.name)

    def test_submit_package_edit_form_valid(self):
        package = self.get_package_by_name(self.package_name)
        res = self.post_package_edit_form(package.id, name=self.package_name_alt)
        assert not json.loads(res.body)
        assert not self.get_package_by_name(self.package_name)
        assert self.get_package_by_name(self.package_name_alt)

    def test_submit_package_edit_form_errors(self):
        package = self.get_package_by_name(self.package_name)
        package_id = package.id
        # Nothing in name.
        invalid_name = ''
        res = self.post_package_edit_form(package_id, name=invalid_name, status=[400])
        # Check package is unchanged.
        assert self.get_package_by_name(self.package_name)
        # Check response is an error form.
        assert "class=\"field_error\"" in res
        form = self.form_from_res(res)
        field_name = 'Package-%s-name' % (package_id)
        self.assert_formfield(form, field_name, invalid_name)

        # Whitespace in name.
        invalid_name = ' '
        res = self.post_package_edit_form(package_id, name=invalid_name, status=[400])
        # Check package is unchanged.
        assert self.get_package_by_name(self.package_name)
        # Check response is an error form.
        assert "class=\"field_error\"" in res
        form = self.form_from_res(res)
        field_name = 'Package-%s-name' % (package_id)
        self.assert_formfield(form, field_name, invalid_name)
        # Check submitting error form with corrected values is OK.
        res = self.post_package_edit_form(package_id, form=form, name=self.package_name_alt)
        assert not json.loads(res.body)
        assert not self.get_package_by_name(self.package_name)
        assert self.get_package_by_name(self.package_name_alt)

    def test_package_create_example_page(self):
        self.ckan_server = self._start_ckan_server()
        try:
            self._wait_for_url('http://127.0.0.1:5000')
            package = self.get_package_by_name(self.package_name)
            package_id = package.id
            res = self.get(url_for(controller='form', action='package_create_example', id=package_id))
            form = res.forms[0]
            self.assert_formfield(form, 'Package--name', '')
            self.set_formfield(form, 'Package--name', self.package_name_alt2)
            form_data = form.submit_fields()
            import urllib
            params = urllib.urlencode(form_data)
            offset = url_for(controller='form', action='package_create_example', id=package_id)
            res = self.app.post(offset, params=params, status=[200], extra_environ=self.extra_environ)
            body = res.body
            assert '<html' in body, "The result does NOT have an HTML doc tag: %s" % body
            assert "Submitted OK" in body, body
        finally:
            self._stop_ckan_server(self.ckan_server)

    def test_package_edit_example_page(self):
        self.ckan_server = self._start_ckan_server()
        try:
            self._wait_for_url('http://127.0.0.1:5000')
            package = self.get_package_by_name(self.package_name)
            package_id = package.id
            res = self.get(url_for(controller='form', action='package_edit_example', id=package_id))
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

    def test_get_harvest_source_create_form(self):
        form = self.get_harvest_source_create_form()
        self.assert_formfield(form, 'HarvestSource--url', '')
        self.assert_formfield(form, 'HarvestSource--description', '')

    def test_submit_harvest_source_create_form_valid(self):
        source_url = u'http://localhost/'
        source_description = u'My harvest source.'
        assert not self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_create_form(url=source_url, description=source_description)
        self.assert_header(res, 'Location')
        # Todo: Check the Location looks promising (extract and check given ID).
        assert not json.loads(res.body)
        source = self.get_harvest_source_by_url(source_url) # Todo: Use extracted ID.
        self.assert_equal(source.user_ref, 'example publisher user')
        self.assert_equal(source.publisher_ref, 'example publisher')

    def test_submit_harvest_source_create_form_invalid(self):
        source_url = u'' # Blank URL.
        assert not self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_create_form(url=source_url, status=[400])
        self.assert_not_header(res, 'Location')
        assert "Url: Please enter a value" in res.body, res.body
        assert not self.get_harvest_source_by_url(source_url, None)

        source_url = u' ' # Not '^http://'
        assert not self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_create_form(url=source_url, status=[400])
        self.assert_not_header(res, 'Location')
        assert "Url: Harvest source URL is invalid" in res.body, res.body
        assert not self.get_harvest_source_by_url(source_url, None)

    def test_get_harvest_source_edit_form(self):
        source_url = u'http://'
        source_description = u'An example harvest source.'
        self.harvest_source = self.create_harvest_source(url=source_url, description=source_description)
        form = self.get_harvest_source_edit_form(self.harvest_source.id)
        self.assert_formfield(form, 'HarvestSource-%s-url' % self.harvest_source.id, source_url)
        self.assert_formfield(form, 'HarvestSource-%s-description' % self.harvest_source.id, source_description)
 
    def test_submit_harvest_source_edit_form_valid(self):
        source_url = u'http://'
        source_description = u'An example harvest source.'
        alt_source_url = u'http://a'
        alt_source_description = u'An old example harvest source.'
        self.harvest_source = self.create_harvest_source(url=source_url, description=source_description)
        assert self.get_harvest_source_by_url(source_url, None)
        assert not self.get_harvest_source_by_url(alt_source_url, None)
        res = self.post_harvest_source_edit_form(self.harvest_source.id, url=alt_source_url, description=alt_source_description)
        self.assert_not_header(res, 'Location')
        # Todo: Check the Location looks promising (extract and check given ID).
        assert not json.loads(res.body)
        assert not self.get_harvest_source_by_url(source_url, None)
        source = self.get_harvest_source_by_url(alt_source_url) # Todo: Use extracted ID.
        assert source
        self.assert_equal(source.user_ref, 'example publisher user')
        self.assert_equal(source.publisher_ref, 'example publisher')

    def test_submit_harvest_source_edit_form_invalid(self):
        source_url = u'http://'
        source_description = u'An example harvest source.'
        alt_source_url = u''
        self.harvest_source = self.create_harvest_source(url=source_url, description=source_description)
        assert self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_edit_form(self.harvest_source.id, url=alt_source_url, status=[400])
        assert self.get_harvest_source_by_url(source_url, None)
        self.assert_not_header(res, 'Location')
        assert "Url: Please enter a value" in res.body, res.body


class TestFormsApi1(Api1TestCase, FormsApiTestCase): pass

class TestFormsApi2(Api2TestCase, FormsApiTestCase): pass

class TestFormsApiUnversioned(ApiUnversionedTestCase, FormsApiTestCase): pass

class WithOrigKeyHeader(FormsApiTestCase):
    apikey_header_name = 'Authorization'

class TestFormsApi1WithOrigKeyHeader(WithOrigKeyHeader, TestFormsApi1): pass

class TestFormsApi2WithOrigKeyHeader(WithOrigKeyHeader, TestFormsApi2): pass

class TestFormsApiUnversionedWithOrigKeyHeader(TestFormsApiUnversioned): pass

