from pylons import config
import webhelpers
import re

from ckan.tests import *
from ckan.tests import search_related
import ckan.model as model
import ckan.authz as authz
from ckan.lib.base import ALLOWED_FIELDSET_PARAMS
from ckan.lib.helpers import url_for
from ckan.lib.helpers import json
from ckan.lib.create_test_data import CreateTestData

ACCESS_DENIED = [403]

# Todo: Test for access control setup. Just checking an object exists in the model doesn't mean it will be presented through the WebUI.

from ckan.tests.functional.api.test_model import ApiControllerTestCase
from ckan.tests.functional.api.test_model import Api1TestCase
from ckan.tests.functional.api.test_model import Api2TestCase
from ckan.tests.functional.api.test_model import ApiUnversionedTestCase

class BaseFormsApiCase(ModelMethods, ApiControllerTestCase):
    api_version = ''
    def split_form_args(self, kwargs):
        '''Splits form keyword arguments into those for the form url
        and those for the fields in the form.'''
        form_url_args = {}
        form_values_args = {}
        for k, v, in kwargs.items():
            if k in ALLOWED_FIELDSET_PARAMS:
                form_url_args[k] = v
            else:
                form_values_args[k] = v
        return form_url_args, form_values_args
    
    def delete_harvest_source(self, url):
        source = self.get_harvest_source_by_url(url, None)
        if source:
            self.delete_commit(source)

    def offset_package_create_form(self, **kwargs):
        url_args, ignore = self.split_form_args(kwargs)
        return self.offset(url_for('/form/package/create', **url_args))

    def offset_package_edit_form(self, ref, **kwargs):
        url_args, ignore = self.split_form_args(kwargs)
        return self.offset(url_for('/form/package/edit/%s' % str(ref), **url_args))

    def offset_harvest_source_create_form(self):
        return self.offset('/form/harvestsource/create')

    def offset_harvest_source_edit_form(self, ref):
        return self.offset('/form/harvestsource/edit/%s' % ref)

    def get_package_create_form(self, status=[200], **form_url_args):
        offset = self.offset_package_create_form(**form_url_args)
        res = self.get(offset, status=status)
        return self.form_from_res(res)

    def get_package_edit_form(self, package_ref, status=[200], **kwargs):
        offset = self.offset_package_edit_form(package_ref, **kwargs)
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
        '''Pass in a resource containing the form and this method returns
        the paster form, which is more easily tested.'''
        assert not "<html>" in str(res.body), "The response is an HTML doc, not just a form: %s" % str(res.body)
        # Arrange 'form fixture' from fieldsets string (helps testing Form API).
        res.body = "<html><form id=\"test\" action=\"\" method=\"post\">" + res.body + "<input type=\"submit\" name=\"send\"></form></html>"
        return res.forms['test']

    def post_package_create_form(self, form=None, status=[201], **kwargs):
        form_url_args, form_field_args = self.split_form_args(kwargs)
        if form == None:
            form = self.get_package_create_form(**form_url_args)
        for key, field_value in form_field_args.items():
            field_name = 'Package--%s' % key
            form[field_name] = field_value
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'log_message': 'Unit-testing the Forms API...',
            'author': 'automated test suite',
        }
        offset = self.offset_package_create_form(**form_url_args)
        return self.post(offset, data, status=status)

    def post_harvest_source_create_form(self, form=None, status=[201], **field_args):
        if form == None:
            form = self.get_harvest_source_create_form()
        for key,field_value in field_args.items():
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

    def post_package_edit_form(self, package_ref, form=None, status=[200], **offset_and_field_args):
        offset_kwargs, field_args = self.split_form_args(offset_and_field_args)
        if form == None:
            form = self.get_package_edit_form(package_ref, **offset_kwargs)
        package_id = self.package_id_from_ref(package_ref)
        for key,field_value in field_args.items():
            field_name = 'Package-%s-%s' % (package_id, key)
            self.set_formfield(form, field_name, field_value)
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'log_message': 'Unit-testing the Forms API...',
            'author': 'automated test suite',
        }
        offset = self.offset_package_edit_form(package_ref, **offset_kwargs)
        return self.post(offset, data, status=status)
        
    def post_harvest_source_edit_form(self, harvest_source_id, form=None, status=[200], **field_args):
        if form == None:
            form = self.get_harvest_source_edit_form(harvest_source_id)
        for key,field_value in field_args.items():
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

    def assert_formfield(self, form, name, expected):
        '''
        Checks the value of a specified form field.
        '''
        assert name in form.fields, 'No field named %r out of:\n%s' % \
               (name, '\n'.join(sorted(form.fields)))
        field = form[name]
        value = field.value
        self.assert_equal(value, expected)

    def assert_not_formfield(self, form, name, expected=None):
        '''
        Checks a specified field does not exist in the form.
        @param expected: ignored (allows for same interface as
                         assert_formfield).
        '''
        assert name not in form.fields, name


class FormsApiTestCase(BaseFormsApiCase):
    def setup(self):
        model.repo.init_db()
        CreateTestData.create()
        self.package_name = u'formsapi'
        self.package_name_alt = u'formsapialt'
        self.package_name_alt2 = u'formsapialt2'
        self.apikey_header_name = config.get('apikey_header_name', 'X-CKAN-API-Key')

        self.user = self.get_user_by_name(u'tester')
        if not self.user:
            self.user = self.create_user(name=u'tester')
        self.extra_environ = {
            self.apikey_header_name : str(self.user.apikey)
        }
        self.create_package(name=self.package_name)
        self.harvest_source = None

    def teardown(self):
        self.purge_package_by_name(self.package_name)
        self.purge_package_by_name(self.package_name_alt)
        self.purge_package_by_name(self.package_name_alt2)
        self.delete_harvest_source(u'http://localhost/')
        if self.harvest_source:
            self.delete_commit(self.harvest_source)
        CreateTestData.delete()
        model.Session.connection().invalidate()
        
    def get_field_names(self, form):
        return form.fields.keys()

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

    def test_submit_full_package_edit_form_valid(self):
        package = self.get_package_by_name(self.package_name)
        data = {
            'name':self.package_name_alt,
            'title':'test title',
            'version':'1.2',
            'url':'http://someurl.com/',
            'notes':'test notes',
            'tags':'sheep goat fish',
            'resources-0-url':'http://someurl.com/download.csv',
            'resources-0-format':'CSV',
            'resources-0-description':'A csv file',
            'author':'Brian',
            'author_email':'brian@company.com',
            'maintainer':'Jim',
            'maintainer_email':'jim@company.com',
            'license_id':'cc-zero',
            'extras-newfield0-key':'genre',
            'extras-newfield0-value':'romance',
            'extras-newfield1-key':'quality',
            'extras-newfield1-value':'high',
            }
        res = self.post_package_edit_form(package.id, **data)
        assert not json.loads(res.body)
        assert not self.get_package_by_name(self.package_name)
        pkg = self.get_package_by_name(self.package_name_alt)
        assert pkg
        for key in data.keys():
            if key.startswith('resources'):
                subkey = key.split('-')[-1]
                pkg_value = getattr(pkg.resources[0], subkey)
            elif key.startswith('extras'):
                ignore, field_name, subkey = key.split('-')
                extra_index = int(field_name[-1])
                if subkey == 'key':
                    continue
                extra_key_subkey = '-'.join(('extras', field_name, 'key'))
                extra_key = data[extra_key_subkey]
                pkg_value = pkg.extras[extra_key]
            elif key == 'tags':
                pkg_value = set([tag.name for tag in pkg.tags])
                data[key] = set(data[key].split())
            else:
                pkg_value = getattr(pkg, key)
            assert pkg_value == data[key], '%r should be %r but is %r' % (key, data[key], pkg_value)

    def test_submit_package_edit_form_errors(self):
        package = self.get_package_by_name(self.package_name)
        package_id = package.id
        # Nothing in name.
        invalid_name = ''
        maintainer_email = "foo@baz.com"
        res = self.post_package_edit_form(package_id,
                                          name=invalid_name,
                                          maintainer_email=maintainer_email,
                                          status=[400])
        # Check package is unchanged.
        assert self.get_package_by_name(self.package_name)
        # Check response is an error form.
        assert "class=\"field_error\"" in res
        form = self.form_from_res(res)
        name_field_name = 'Package-%s-name' % (package_id)
        maintainer_field_name = 'Package-%s-maintainer_email' % (package_id)
        # this test used to be 
        #   self.assert_formfield(form, field_name, invalid_name)
        # but since the formalchemy upgrade, we no longer sync data to
        # the model if the validation fails (as this would cause an
        # IntegrityError at the database level).
        # and formalchemy.fields.FieldRenderer.value renders the model
        # value if the passed in value is an empty string
        self.assert_formfield(form, name_field_name, package.name)
        # however, other fields which aren't blank should be preserved
        self.assert_formfield(form, maintainer_field_name, maintainer_email)

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

    @search_related
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

    @search_related
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

