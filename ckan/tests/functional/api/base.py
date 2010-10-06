from pylons import config
import webhelpers.util
import re

from ckan.tests import *
from ckan.tests import TestController as ControllerTestCase
import ckan.model as model
import ckan.authz as authz
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.helpers import json

ACCESS_DENIED = [403]

class ApiControllerTestCase(ControllerTestCase):

    send_authorization_header = True
    extra_environ = {}

    api_version = None
    ref_package_by = ''
    ref_group_by = ''

    def get(self, offset, status=[200]):
        response = self.app.get(offset, status=status,
            extra_environ=self.get_extra_environ())
        return response

    def post(self, offset, data, status=[200,201], *args, **kwds):
        params = '%s=1' % json.dumps(data)
        response = self.app.post(offset, params=params, status=status,
            extra_environ=self.get_extra_environ())
        return response

    def app_delete(self, offset, status=[200,201], *args, **kwds):
        response = self.app.delete(offset, status=status,
            extra_environ=self.get_extra_environ())
        return response

    def get_extra_environ(self):
        extra_environ = {}
        for (key,value) in self.extra_environ.items():
            if key == 'Authorization':
                if self.send_authorization_header == True:
                    extra_environ[key] = value
            else:
                extra_environ[key] = value
        return extra_environ

    @classmethod
    def offset(self, path):
        assert self.api_version != None, "API version is missing."
        base = '/api'
        if self.api_version:
            base += '/' + self.api_version
        return '%s%s' % (base, path)

    def package_offset(self, package_name=None):
        if package_name == None:
            # Package Register
            return self.offset('/rest/package')
        else:
            # Package Entity
            package_ref = self.package_ref_from_name(package_name)
            return self.offset('/rest/package/%s' % package_ref)

    def package_ref_from_name(self, package_name):
        package = self.get_package_by_name(unicode(package_name))
        if package == None:
            return package_name
        else:
            return self.ref_package(package)

    def package_id_from_ref(self, package_name):
        package = self.get_package_by_name(unicode(package_name))
        if package == None:
            return package_name
        else:
            return self.ref_package(package)

    def ref_package(self, package):
        assert self.ref_package_by in ['id', 'name']
        return getattr(package, self.ref_package_by)

    def group_ref_from_name(self, group_name):
        group = self.get_group_by_name(unicode(group_name))
        if group == None:
            return group_name
        else:
            return self.ref_group(group)

    def ref_group(self, group):
        assert self.ref_group_by in ['id', 'name']
        return getattr(group, self.ref_group_by)

    def anna_offset(self, postfix=''):
        return self.package_offset('annakarenina') + postfix

    def assert_msg_represents_anna(self, msg):
        assert 'annakarenina' in msg, msg
        assert '"license_id": "other-open"' in msg, str(msg)
        assert 'russian' in msg, msg
        assert 'tolstoy' in msg, msg
        assert '"extras": {' in msg, msg
        assert '"genre": "romantic novel"' in msg, msg
        assert '"original media": "book"' in msg, msg
        assert 'annakarenina.com/download' in msg, msg
        assert '"plain text"' in msg, msg
        assert '"Index of the novel"' in msg, msg
        assert '"id": "%s"' % self.anna.id in msg, msg
        expected = '"groups": ['
        assert expected in msg, (expected, msg)
        expected = self.group_ref_from_name('roger')
        assert expected in msg, (expected, msg)
        expected = self.group_ref_from_name('david')
        assert expected in msg, (expected, msg)

    def data_from_res(self, res):
        return json.loads(res.body)

    def get_expected_api_version(self):
        return self.api_version


class Api1TestCase(ApiControllerTestCase):

    api_version = '1'
    ref_package_by = 'name'
    ref_group_by = 'name'

    def assert_msg_represents_anna(self, msg):
        super(Api1TestCase, self).assert_msg_represents_anna(msg)
        assert '"download_url": "http://www.annakarenina.com/download/x=1&y=2"' in msg, msg


class Api2TestCase(ApiControllerTestCase):

    api_version = '2'
    ref_package_by = 'id'
    ref_group_by = 'id'

    def assert_msg_represents_anna(self, msg):
        super(Api2TestCase, self).assert_msg_represents_anna(msg)
        assert 'download_url' not in msg, msg


class ApiUnversionedTestCase(Api1TestCase):

    api_version = ''
    oldest_api_version = '1'

    def get_expected_api_version(self):
        return self.oldest_api_version

