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

    STATUS_200_OK = 200
    STATUS_400_BAD_REQUEST = 400
    STATUS_403_ACCESS_DENIED = 403
    STATUS_409_CONFLICT = 409

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
        params = '%s=1' % self.dumps(data)
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
        data = self.loads(msg)
        self.assert_equal(data['name'], 'annakarenina')
        self.assert_equal(data['license_id'], 'other-open')
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

        # Todo: What is the deal with ckan_url? And should this use IDs rather than names?
        assert 'ckan_url' in msg
        assert '"ckan_url": "http://test.ckan.net/package/annakarenina"' in msg, msg

    def data_from_res(self, res):
        return self.loads(res.body)

    def get_expected_api_version(self):
        return self.api_version

    def dumps(self, data):
        return json.dumps(data)

    def loads(self, chars):
        try:
            return json.loads(chars)
        except ValueError, inst:
            raise Exception, "Couldn't loads string '%s': %s" % (chars, inst)

# Todo: Rename to Version1TestCase.
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


class BaseModelApiTestCase(ModelMethods, ApiControllerTestCase):

    commit_changesets = True

    require_common_fixtures = True
    # Todo: Eventually reuse_common_fixtures = True.
    reuse_common_fixtures = False
    has_common_fixtures = False

    testpackage_license_id = u'gpl-3.0'
    testpackagevalues = {
        'name' : u'testpkg',
        'title': u'Some Title',
        'url': u'http://blahblahblah.mydomain',
        'resources': [{
            u'url':u'http://blah.com/file.xml',
            u'format':u'xml',
            u'description':u'Main file',
            u'hash':u'abc123',
        }, {
            u'url':u'http://blah.com/file2.xml',
            u'format':u'xml',
            u'description':u'Second file',
            u'hash':u'def123',
        }],
        'tags': [u'russion', u'novel'],
        'license_id': testpackage_license_id,
        'extras': {
            'genre' : u'horror',
            'media' : u'dvd',
        },
    }
    testgroupvalues = {
        'name' : u'testgroup',
        'title' : u'Some Group Title',
        'description' : u'Great group!',
        'packages' : [u'annakarenina', u'warandpeace'],
    }
    testharvestsourcevalues = {
        'url' : u'http://localhost/',
        'description' : u'My metadata.',
        'user_ref': u'a_publisher_user',
        'publisher_ref': u'a_publisher',
    }
    testharvestingjobvalues = {
        'user_ref': u'a_publisher_user',
    }
    user_name = u'http://myrandom.openidservice.org/'

    def conditional_create_common_fixtures(self):
        if self.require_common_fixtures and not BaseModelApiTestCase.has_common_fixtures:
            self.create_common_fixtures()
            BaseModelApiTestCase.has_common_fixtures = True

    def create_common_fixtures(self):
        CreateTestData.create(commit_changesets=self.commit_changesets)
        CreateTestData.create_arbitrary([], extra_user_names=[self.user_name])

    def reuse_or_delete_common_fixtures(self):
        if BaseModelApiTestCase.has_common_fixtures and not self.reuse_common_fixtures:
            raise Exception, "Blah"
            BaseModelApiTestCase.has_common_fixtures = False
            self.delete_common_fixtures()
            self.commit_remove()

    def delete_common_fixtures(self):
        CreateTestData.delete()

    def init_extra_environ(self):
        self.user = model.User.by_name(self.user_name)
        self.extra_environ={'Authorization' : str(self.user.apikey)}

