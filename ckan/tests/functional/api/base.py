import re
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from pylons import config
import webhelpers.util
from nose.tools import assert_equal
from paste.fixture import TestRequest

from ckan.tests import *
import ckan.model as model
import ckan.authz as authz
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.helpers import json, url_escape
from ckan.tests import TestController as ControllerTestCase

ACCESS_DENIED = [403]

class ApiTestCase(object):

    STATUS_200_OK = 200
    STATUS_201_CREATED = 201
    STATUS_400_BAD_REQUEST = 400
    STATUS_403_ACCESS_DENIED = 403
    STATUS_404_NOT_FOUND = 404
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
        params = '%s=1' % url_escape(self.dumps(data))
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
        assert '"ckan_url": "http://test.ckan.net/dataset/annakarenina"' in msg, msg

    def assert_msg_represents_roger(self, msg):
        assert 'roger' in msg, msg
        data = self.loads(msg)
        keys = set(data.keys())
        expected_keys = set(['id', 'name', 'title', 'description', 'created',
                            'state', 'revision_id', 'packages'])
        missing_keys = expected_keys - keys
        assert not missing_keys, missing_keys
        assert_equal(data['name'], 'roger')
        assert_equal(data['title'], 'Roger\'s books')
        assert_equal(data['description'], 'Roger likes these books.')
        assert_equal(data['state'], 'active')
        assert_equal(data['packages'], [self._ref_package(self.anna)])

    def assert_msg_represents_russian(self, msg):
        data = self.loads(msg)
        pkgs = set(data)
        expected_pkgs = set([self.package_ref_from_name('annakarenina'),
                             self.package_ref_from_name('warandpeace')])
        differences = expected_pkgs ^ pkgs
        assert not differences, '%r != %r' % (pkgs, expected_pkgs)

    def data_from_res(self, res):
        return self.loads(res.body)

    def package_ref_from_name(self, package_name):
        package = self.get_package_by_name(unicode(package_name))
        if package is None:
            return package_name
        else:
            return self.ref_package(package)

    def package_id_from_ref(self, package_name):
        package = self.get_package_by_name(unicode(package_name))
        if package is None:
            return package_name
        else:
            return self.ref_package(package)

    def ref_package(self, package):
        assert self.ref_package_by in ['id', 'name']
        return getattr(package, self.ref_package_by)

    def get_expected_api_version(self):
        return self.api_version

    def dumps(self, data):
        return json.dumps(data)

    def loads(self, chars):
        try:
            return json.loads(chars)
        except ValueError, inst:
            raise Exception, "Couldn't loads string '%s': %s" % (chars, inst)

    def assert_json_response(self, res, expected_in_body=None):
        content_type = res.header_dict['Content-Type']
        assert 'application/json' in content_type, content_type
        res_json = self.loads(res.body)
        if expected_in_body:
            assert expected_in_body in res_json or \
                   expected_in_body in str(res_json), \
                   'Expected to find %r in JSON response %r' % \
                   (expected_in_body, res_json)

class Api1and2TestCase(object):
    ''' Utils for v1 and v2 API.
          * RESTful URL utils
    '''
    def package_offset(self, package_name=None):
        if package_name is None:
            # Package Register
            return self.offset('/rest/dataset')
        else:
            # Package Entity
            package_ref = self.package_ref_from_name(package_name)
            return self.offset('/rest/dataset/%s' % package_ref)

    def group_offset(self, group_name=None):
        if group_name is None:
            # Group Register
            return self.offset('/rest/group')
        else:
            # Group Entity
            group_ref = self.group_ref_from_name(group_name)
            return self.offset('/rest/group/%s' % group_ref)

    def group_ref_from_name(self, group_name):
        group = self.get_group_by_name(unicode(group_name))
        if group is None:
            return group_name
        else:
            return self.ref_group(group)

    def ref_group(self, group):
        assert self.ref_group_by in ['id', 'name']
        return getattr(group, self.ref_group_by)

    def revision_offset(self, revision_id=None):
        if revision_id is None:
            # Revision Register
            return self.offset('/rest/revision')
        else:
            # Revision Entity
            return self.offset('/rest/revision/%s' % revision_id)

    def rating_offset(self, package_name=None):
        if package_name is None:
            # Revision Register
            return self.offset('/rest/rating')
        else:
            # Revision Entity
            package_ref = self.package_ref_from_name(package_name)
            return self.offset('/rest/rating/%s' % package_ref)

    def relationship_offset(self, package_1_name=None,
                            relationship_type=None,
                            package_2_name=None,
                            ):
        assert package_1_name
        package_1_ref = self.package_ref_from_name(package_1_name)
        if package_2_name is None:
            if not relationship_type:
                return self.offset('/rest/dataset/%s/relationships' % \
                                   package_1_ref)
            else:
                return self.offset('/rest/dataset/%s/%s' %
                                   (package_1_ref, relationship_type))
        else:
            package_2_ref = self.package_ref_from_name(package_2_name)
            if not relationship_type:
                return self.offset('/rest/dataset/%s/relationships/%s' % \
                                   (package_1_ref, package_2_ref))
            else:
                return self.offset('/rest/dataset/%s/%s/%s' % \
                                   (package_1_ref,
                                    relationship_type,
                                    package_2_ref))

    def anna_offset(self, postfix=''):
        return self.package_offset('annakarenina') + postfix

    def tag_offset(self, tag_name=None):
        if tag_name is None:
            # Tag Register
            return self.offset('/rest/tag')
        else:
            # Tag Entity
            tag_ref = self.tag_ref_from_name(tag_name)
            return self.offset('/rest/tag/%s' % tag_ref)

    def tag_ref_from_name(self, tag_name):
        tag = self.get_tag_by_name(unicode(tag_name))
        if tag is None:
            return tag_name
        else:
            return self.ref_tag(tag)

    def ref_tag(self, tag):
        assert self.ref_tag_by in ['id', 'name']
        return getattr(tag, self.ref_tag_by)

    @classmethod
    def _ref_package(cls, package):
        assert cls.ref_package_by in ['id', 'name']
        return getattr(package, cls.ref_package_by)

    @classmethod
    def _ref_group(cls, group):
        assert cls.ref_group_by in ['id', 'name']
        return getattr(group, cls.ref_group_by)

    @classmethod
    def _list_package_refs(cls, packages):
        return [getattr(p, cls.ref_package_by) for p in packages]

    @classmethod
    def _list_group_refs(cls, groups):
        return [getattr(p, cls.ref_group_by) for p in groups]

class Api1TestCase(Api1and2TestCase):

    api_version = '1'
    ref_package_by = 'name'
    ref_group_by = 'name'
    ref_tag_by = 'name'

    def assert_msg_represents_anna(self, msg):
        super(Api1TestCase, self).assert_msg_represents_anna(msg)
        assert '"download_url": "http://www.annakarenina.com/download/x=1&y=2"' in msg, msg


class Api2TestCase(Api1and2TestCase):

    api_version = '2'
    ref_package_by = 'id'
    ref_group_by = 'id'
    ref_tag_by = 'id'

    def assert_msg_represents_anna(self, msg):
        super(Api2TestCase, self).assert_msg_represents_anna(msg)
        assert 'download_url' not in msg, msg


class Api3TestCase(ApiTestCase):

    api_version = '3'
    ref_package_by = 'name'
    ref_group_by = 'name'
    ref_tag_by = 'name'

    def assert_msg_represents_anna(self, msg):
        super(Api2TestCase, self).assert_msg_represents_anna(msg)
        assert 'download_url' not in msg, msg

class ApiUnversionedTestCase(Api1TestCase):

    api_version = ''
    oldest_api_version = '1'

    def get_expected_api_version(self):
        return self.oldest_api_version


class BaseModelApiTestCase(ModelMethods, ApiTestCase, ControllerTestCase):

    testpackage_license_id = u'gpl-3.0'
    package_fixture_data = {
        'name' : u'testpkg',
        'title': u'Some Title',
        'url': u'http://blahblahblah.mydomain',
        'resources': [{
            u'url':u'http://blah.com/file.xml',
            u'format':u'xml',
            u'description':u'Main file',
            u'hash':u'abc123',
            u'alt_url':u'alt_url',
            u'size_extra':u'200',
        }, {
            u'url':u'http://blah.com/file2.xml',
            u'format':u'xml',
            u'description':u'Second file',
            u'hash':u'def123',
            u'alt_url':u'alt_url',
            u'size_extra':u'200',
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
    user_name = u'http://myrandom.openidservice.org/'

    def setup(self):
        super(BaseModelApiTestCase, self).setup()
        self.conditional_create_common_fixtures()
        self.init_extra_environ()

    def teardown(self):
        model.Session.remove()
        model.repo.rebuild_db()
        super(BaseModelApiTestCase, self).teardown()

    def init_extra_environ(self):
        self.user = model.User.by_name(self.user_name)
        self.extra_environ={'Authorization' : str(self.user.apikey)}

    def post_json(self, offset, data, status=None, extra_environ=None):
        ''' Posts data in the body in application/json format, used by
        javascript libraries.
        (rather than Paste Fixture\'s default format of
        application/x-www-form-urlencoded)

        '''
        return self.http_request(offset, data, content_type='application/json',
                                 request_method='POST',
                                 content_length=len(data),
                                 status=status, extra_environ=extra_environ)

    def delete_request(self, offset, status=None, extra_environ=None):
        ''' Sends a delete request. Similar to the paste.delete but it
        does not send the content type or content length.
        '''
        return self.http_request(offset, data='', content_type=None,
                                 request_method='DELETE',
                                 content_length=None,
                                 status=status,
                                 extra_environ=extra_environ)

    def http_request(self, offset, data,
                     content_type='application/json',
                     request_method='POST',
                     content_length=None,
                     status=None,
                     extra_environ=None):
        ''' Posts data in the body in a user-specified format.
        (rather than Paste Fixture\'s default Content-Type of
        application/x-www-form-urlencoded)

        '''
        environ = self.app._make_environ()
        if content_type:
            environ['CONTENT_TYPE'] = content_type
        if content_length is not None:
            environ['CONTENT_LENGTH'] = str(content_length)
        environ['REQUEST_METHOD'] = request_method
        environ['wsgi.input'] = StringIO(data)
        if extra_environ:
            environ.update(extra_environ)
        self.app._set_headers({}, environ)
        req = TestRequest(offset, environ, expect_errors=False)
        return self.app.do_request(req, status=status)        
