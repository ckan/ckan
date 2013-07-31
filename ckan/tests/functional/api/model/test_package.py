import copy

from nose.tools import assert_equal, assert_raises

from ckan.lib.create_test_data import CreateTestData
import ckan.lib.search as search
from ckan.lib.search.common import SolrSettings

from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase

import ckan.tests as tests

# Todo: Remove this ckan.model stuff.
import ckan.model as model

class PackagesTestCase(BaseModelApiTestCase):

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.user_name = u'annafan' # created in CreateTestData
        cls.init_extra_environ(cls.user_name)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def teardown(self):
        self.purge_package_by_name(self.package_fixture_data['name'])

    def get_groups_identifiers(self, test_groups, users=[]):
        groups = []
        for grp in test_groups:
            group = model.Group.get(grp)
            if self.get_expected_api_version() == 1:
                groups.append(group.name)
            else:
                groups.append(group.id)

            if users:
                model.setup_default_user_roles(group, users)
        return groups

    def test_register_get_ok(self):
        offset = self.package_offset()
        res = self.app.get(offset, status=self.STATUS_200_OK)
        assert self.ref_package(self.anna) in res, res
        assert self.ref_package(self.war) in res, res

    def test_register_post_ok(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_201_CREATED,
                            extra_environ=self.admin_extra_environ)

        # Check the returned package is as expected
        pkg = self.loads(res.body)
        assert_equal(pkg['name'], self.package_fixture_data['name'])
        assert_equal(pkg['title'], self.package_fixture_data['title'])
        assert_equal(set(pkg['tags']), set(self.package_fixture_data['tags']))
        assert_equal(len(pkg['resources']), len(self.package_fixture_data['resources']))
        assert_equal(pkg['extras'], self.package_fixture_data['extras'])

        # Check the value of the Location header.
        location = res.header('Location')

        assert offset in location
        res = self.app.get(location, status=self.STATUS_200_OK)
        # Check the database record.
        model.Session.remove()
        package = self.get_package_by_name(self.package_fixture_data['name'])
        assert package
        self.assert_equal(package.title, self.package_fixture_data['title'])
        self.assert_equal(package.url, self.package_fixture_data['url'])
        self.assert_equal(package.license_id, self.testpackage_license_id)
        self.assert_equal(len(package.get_tags()), 2)
        self.assert_equal(len(package.extras), 2)
        for key, value in self.package_fixture_data['extras'].items():
            self.assert_equal(package.extras[key], value)
        self.assert_equal(len(package.resources), len(self.package_fixture_data['resources']))
        for (i, expected_resource) in enumerate(self.package_fixture_data['resources']):
            package_resource = package.resources[i]
            for key in expected_resource.keys():
                if key == 'extras':
                    package_resource_extras = getattr(package_resource, key)
                    expected_resource_extras = expected_resource[key].items()
                    for expected_extras_key, expected_extras_value in expected_resource_extras:
                        package_resource_value = package_resource_extras[expected_extras_key],\
                         'Package:%r Extras:%r Expected_extras:%r' % \
                         (self.package_fixture_data['name'],
                          package_resource_extras, expected_resource)
                else:
                    package_resource_value = getattr(package_resource, key, None)
                    if not package_resource_value:
                        package_resource_value = package_resource.extras[key]

                    expected_resource_value = expected_resource[key]
                    self.assert_equal(package_resource_value, expected_resource_value)

        # Test Package Entity Get 200.
        offset = self.package_offset(self.package_fixture_data['name'])
        res = self.app.get(offset, status=self.STATUS_200_OK)
        # Todo: Instead loads() the data and then check actual values.
        assert self.package_fixture_data['name'] in res, res
        assert '"license_id": "%s"' % self.package_fixture_data['license_id'] in res, res
        assert self.package_fixture_data['tags'][0] in res, res
        assert self.package_fixture_data['tags'][1] in res, res
        assert '"extras": {' in res, res
        for key, value in self.package_fixture_data['extras'].items():
            assert '"%s": "%s"' % (key, value) in res, res

        model.Session.remove()

        # Test Packages Register Post 409 (conflict - create duplicate package).
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams, status=self.STATUS_409_CONFLICT,
                extra_environ=self.admin_extra_environ)
        model.Session.remove()

    def test_register_post_with_group(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()

        test_groups = [u'david']
        user = model.User.by_name(u'testsysadmin')

        groups = self.get_groups_identifiers(test_groups,[user])

        package_fixture_data = self.package_fixture_data
        package_fixture_data['groups'] = groups
        data = self.dumps(package_fixture_data)
        res = self.post_json(offset, data, status=self.STATUS_201_CREATED,
                             extra_environ={'Authorization':str(user.apikey)})

        # Check the database record.
        model.Session.remove()
        package = self.get_package_by_name(self.package_fixture_data['name'])
        assert package
        pkg_groups = model.Session.query(model.Group).\
                    join(model.Member, model.Member.group_id == model.Group.id).\
                    filter(model.Member.table_id == package.id).all()
        if self.get_expected_api_version() == 1:
            self.assert_equal([g.name for g in pkg_groups], groups)
        else:
            self.assert_equal([g.id for g in pkg_groups], groups)
        del package_fixture_data['groups']

    def test_register_post_with_group_not_authorized(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()

        test_groups = [u'david']
        groups = self.get_groups_identifiers(test_groups)

        package_fixture_data = self.package_fixture_data
        package_fixture_data['groups'] = groups
        data = self.dumps(package_fixture_data)
        res = self.post_json(offset, data, status=self.STATUS_403_ACCESS_DENIED,
                             extra_environ=self.extra_environ)
        del package_fixture_data['groups']

    def test_register_post_with_group_not_found(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()

        test_groups = [u'this-group-does-not-exist']
        groups = test_groups

        package_fixture_data = self.package_fixture_data
        package_fixture_data['groups'] = groups
        data = self.dumps(package_fixture_data)
        res = self.post_json(offset, data, status=self.STATUS_404_NOT_FOUND,
                             extra_environ=self.extra_environ)
        del package_fixture_data['groups']

    def test_register_post_with_group_sysadmin(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()
        user = model.User.by_name(u'testsysadmin')
        test_groups = [u'david']
        groups = self.get_groups_identifiers(test_groups)

        package_fixture_data = self.package_fixture_data
        package_fixture_data['groups'] = groups
        data = self.dumps(package_fixture_data)
        res = self.post_json(offset, data, status=self.STATUS_201_CREATED,
                              extra_environ={'Authorization':str(user.apikey)})
        # Check the database record.
        model.Session.remove()
        package = self.get_package_by_name(self.package_fixture_data['name'])
        assert package
        pkg_groups = model.Session.query(model.Group).\
                    join(model.Member, model.Member.group_id == model.Group.id).\
                    filter(model.Member.table_id == package.id).all()
        if self.get_expected_api_version() == 1:
            self.assert_equal([g.name for g in pkg_groups], groups)
        else:
            self.assert_equal([g.id for g in pkg_groups], groups)

        del package_fixture_data['groups']

    def test_register_post_json(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()
        data = self.dumps(self.package_fixture_data)
        res = self.post_json(offset, data, status=self.STATUS_201_CREATED,
                             extra_environ=self.admin_extra_environ)
        # Check the database record.
        model.Session.remove()
        package = self.get_package_by_name(self.package_fixture_data['name'])
        assert package
        self.assert_equal(package.title, self.package_fixture_data['title'])

    def test_register_post_bad_content_type(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()
        data = self.dumps(self.package_fixture_data)
        res = self.http_request(offset, data,
                                content_type='something/unheard_of',
                                status=[self.STATUS_400_BAD_REQUEST,
                                        self.STATUS_201_CREATED],
                                extra_environ=self.admin_extra_environ)
        model.Session.remove()
        # Some versions of webob work, some don't. No matter, we record this
        # behaviour.
        package = self.get_package_by_name(self.package_fixture_data['name'])
        if res.status == self.STATUS_400_BAD_REQUEST:
            # Check there is no database record.
            assert not package
        else:
            assert package

    def test_register_post_bad_request(self):
        test_params = {
            'name':u'testpackage06_400',
            'resources':[u'should_be_a_dict'],
        }
        offset = self.offset('/rest/dataset')
        postparams = '%s=1' % self.dumps(test_params)
        res = self.app.post(offset, params=postparams, status=self.STATUS_400_BAD_REQUEST,
                extra_environ=self.admin_extra_environ)

    def test_register_post_denied(self):
        offset = self.offset('/rest/dataset')
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams, status=self.STATUS_403_ACCESS_DENIED)

    def test_register_post_readonly_fields(self):
        # (ticket 662) Post a package with readonly field such as 'id'
        offset = self.offset('/rest/dataset')
        data = {'name': u'test_readonly',
                'id': u'not allowed to be set',
                }
        postparams = '%s=1' % self.dumps(data)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_409_CONFLICT,
                            extra_environ=self.admin_extra_environ)
        assert_equal(res.body, '{"id": ["The input field id was not expected."]}')

    def test_register_post_indexerror(self):
        """
        Test that we can't add a package if Solr is down.
        """
        bad_solr_url = 'http://127.0.0.1/badsolrurl'
        original_settings = SolrSettings.get()[0]
        try:
            SolrSettings.init(bad_solr_url)

            assert not self.get_package_by_name(self.package_fixture_data['name'])
            offset = self.package_offset()
            data = self.dumps(self.package_fixture_data)

            self.post_json(offset, data, status=500, extra_environ=self.admin_extra_environ)
            model.Session.remove()
        finally:
            SolrSettings.init(original_settings)

    def test_register_post_tag_too_long(self):
        pkg = {'name': 'test_tag_too_long',
               'tags': ['tagok', 't'*101]}
        assert not self.get_package_by_name(pkg['name'])
        offset = self.package_offset()
        data = self.dumps(pkg)
        res = self.post_json(offset, data, status=self.STATUS_409_CONFLICT,
                             extra_environ=self.admin_extra_environ)
        assert 'length is more than maximum 100' in res.body, res.body
        assert 'tagok' not in res.body

    def test_entity_get_ok(self):
        package_refs = [self.anna.name, self.anna.id]
        for ref in package_refs:
            offset = self.offset('/rest/dataset/%s' % ref)
            res = self.app.get(offset, status=self.STATUS_200_OK)
            self.assert_msg_represents_anna(msg=res.body)

    def test_entity_get_ok_jsonp(self):
        offset = self.anna_offset(postfix='?callback=jsoncallback')
        res = self.app.get(offset, status=self.STATUS_200_OK)
        import re
        assert re.match('jsoncallback\(.*\);', res.body), res
        # Unwrap JSONP callback (we want to look at the data).
        msg = res.body[len('jsoncallback')+1:-2]
        self.assert_msg_represents_anna(msg=msg)

    def test_entity_get_not_found(self):
        offset = self.offset('/rest/dataset/22222')
        res = self.app.get(offset, status=self.STATUS_404_NOT_FOUND)
        model.Session.remove()

    def test_entity_get_then_post(self):
        # (ticket 662) Ensure an entity you 'get' from a register can be
        # returned by posting it back
        offset = self.package_offset(self.war.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        data = self.loads(res.body)

        postparams = '%s=1' % self.dumps(data)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_200_OK,
                            extra_environ=self.admin_extra_environ)
        data_returned = self.loads(res.body)
        assert_equal(data['name'], data_returned['name'])
        assert_equal(data['license_id'], data_returned['license_id'])

    def test_entity_get_then_post_new(self):
        offset = self.package_offset(self.war.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        data = self.loads(res.body)

        # change name and create a new package
        data['name'] = u'newpkg'
        data['id'] = None # ensure this doesn't clash or you get 409 error
        postparams = '%s=1' % self.dumps(data)
        # use russianfan now because he has rights to add this package to
        # the 'david' group.
        extra_environ = {'REMOTE_USER': 'testsysadmin'}
        res = self.app.post(self.package_offset(), params=postparams,
                            status=self.STATUS_201_CREATED,
                            extra_environ=extra_environ)
        try:
            data_returned = self.loads(res.body)
            assert_equal(data['name'], data_returned['name'])
            assert_equal(data['license_id'], data_returned['license_id'])
        finally:
            self.purge_package_by_name(data['name'])

    def test_entity_post_changed_readonly(self):
        # (ticket 662) Edit a readonly field gives error
        offset = self.package_offset(self.war.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        data = self.loads(res.body)
        data['id'] = 'illegally changed value'
        postparams = '%s=1' % self.dumps(data)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_409_CONFLICT,
                            extra_environ=self.admin_extra_environ)
        assert "Cannot change value of key from" in res.body, res.body
        assert "to illegally changed value. This key is read-only" in res.body, res.body

    def test_entity_update_denied(self):
        offset = self.anna_offset()
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams, status=self.STATUS_403_ACCESS_DENIED)

    def test_entity_delete_denied(self):
        offset = self.anna_offset()
        res = self.app.delete(offset, status=self.STATUS_403_ACCESS_DENIED)

    def test_09_update_package_entity_not_found(self):
        offset = self.offset('/rest/dataset/22222')
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_404_NOT_FOUND,
                            extra_environ=self.admin_extra_environ)

    def create_package_with_admin_user(self, package_data):
        '''Creates a package with self.user as admin and provided package_data.
        '''
        self.create_package(admins=[self.user], data=package_data)

    def assert_package_update_ok(self, package_ref_attribute,
                                 method_str):
        old_fixture_data = {
            'name': self.package_fixture_data['name'],
            'url': self.package_fixture_data['url'],
            'tags': [u'tag 1.1', u'tag2', u'tag3'],
            'extras': {
                u'key1': u'val1',
                u'key2': u'val2'
            },
        }
        new_fixture_data = {
            'name':u'somethingnew',
            'title':u'newtesttitle',
            'resources': [{
                u'url':u'http://blah.com/file2.xml',
                u'format':u'xml',
                u'description':u'Appendix 1',
                u'hash':u'def123',
                u'alt_url':u'alt123',
                u'size_extra':u'400',
            },{
                u'url':u'http://blah.com/file3.xml',
                u'format':u'xml',
                u'description':u'Appenddic 2',
                u'hash':u'ghi123',
                u'alt_url':u'alt123',
                u'size_extra':u'400',
            }],
            'extras': {
                u'key3': u'val3',
                u'key4': u'',
                u'key2': None,
                u'key7': '["a","b"]',
             },
            'tags': [u'tag 1.1', u'tag2', u'tag 4', u'tag5.'],
        }
        self.create_package_with_admin_user(old_fixture_data)
        pkg = self.get_package_by_name(old_fixture_data['name'])
        # This is the one occasion where we reference package explicitly
        # by name or ID, rather than use the value from self.ref_package_by
        # because you should be able to specify the package both ways round
        # for both versions of the API.
        package_ref = getattr(pkg, package_ref_attribute)
        offset = self.offset('/rest/dataset/%s' % package_ref)
        params = '%s=1' % self.dumps(new_fixture_data)
        method_func = getattr(self.app, method_str)
        res = method_func(offset, params=params, status=self.STATUS_200_OK,
                          extra_environ=self.admin_extra_environ)

        try:
            # Check the returned package is as expected
            pkg = self.loads(res.body)
            assert_equal(pkg['name'], new_fixture_data['name'])
            assert_equal(pkg['title'], new_fixture_data['title'])
            assert_equal(set(pkg['tags']), set(new_fixture_data['tags']))
            assert_equal(len(pkg['resources']), len(new_fixture_data['resources']))
            expected_extras = copy.deepcopy(new_fixture_data['extras'])
            del expected_extras['key2']
            expected_extras['key1'] = old_fixture_data['extras']['key1']
            assert_equal(pkg['extras'], expected_extras)

            # Check submitted field have changed.
            model.Session.remove()
            package = self.get_package_by_name(new_fixture_data['name'])
            # - title
            self.assert_equal(package.title, new_fixture_data['title'])
            # - tags
            package_tagnames = [tag.name for tag in package.get_tags()]
            for tagname in new_fixture_data['tags']:
                assert tagname in package_tagnames, 'tag %r not in %r' % (tagname, package_tagnames)
            # - resources
            assert len(package.resources), "Package has no resources: %s" % package
            self.assert_equal(len(package.resources), 2)
            resource = package.resources[0]
            self.assert_equal(resource.url, u'http://blah.com/file2.xml')
            self.assert_equal(resource.format, u'xml')
            self.assert_equal(resource.description, u'Appendix 1')
            self.assert_equal(resource.hash, u'def123')
            self.assert_equal(resource.alt_url, u'alt123')
            self.assert_equal(resource.extras['size_extra'], u'400')
            resource = package.resources[1]
            self.assert_equal(resource.url, 'http://blah.com/file3.xml')
            self.assert_equal(resource.format, u'xml')
            self.assert_equal(resource.description, u'Appenddic 2')
            self.assert_equal(resource.hash, u'ghi123')
            self.assert_equal(resource.alt_url, u'alt123')
            self.assert_equal(resource.extras['size_extra'], u'400')

            # Check unsubmitted fields have not changed.
            # - url
            self.assert_equal(package.url, self.package_fixture_data['url'])
            # - extras

            self.assert_equal(len(package.extras), 4)
            for key, value in {u'key1':u'val1',
                               u'key3':u'val3',
                               u'key7':'["a","b"]',
                               u'key4':u''}.items():
                self.assert_equal(package.extras[key], value)
            # NB: key4 set to '' creates it
            # but: key2 set to None will delete it
            assert not package.extras.has_key('key2')
        finally:
            self.purge_package_by_name(new_fixture_data['name'])


    def test_package_update_ok_by_id(self):
        self.assert_package_update_ok('id', 'post')

    def test_entity_update_ok_by_name(self):
        self.assert_package_update_ok('name', 'post')

    def test_package_update_ok_by_id_by_put(self):
        self.assert_package_update_ok('id', 'put')

    def test_entity_update_ok_by_name_by_put(self):
        self.assert_package_update_ok('name', 'put')

    def test_package_update_invalid(self):
        old_fixture_data = {
            'name': self.package_fixture_data['name'],
        }
        new_fixture_data = {
            'name':u'somethingnew',
            'resources': [{
                u'url':u'http://blah.com/file1.xml',
                u'size':u'abc', # INVALID
            },{
                u'url':u'http://blah.com/file2.xml',
                u'size':u'400',
                u'last_modified':u'123', # INVALID
            }],
        }
        self.create_package_with_admin_user(old_fixture_data)
        pkg = self.get_package_by_name(old_fixture_data['name'])
        offset = self.offset('/rest/dataset/%s' % pkg.name)
        params = '%s=1' % self.dumps(new_fixture_data)
        res = self.app.post(offset, params=params,
                            status=self.STATUS_409_CONFLICT,
                            extra_environ=self.admin_extra_environ)
        res_dict = self.loads(res.body)
        assert len(res_dict['resources']) == 2, res_dict['resources']
        assert_equal(res_dict['resources'][0], {u'size': [u'Invalid integer']})
        assert_equal(res_dict['resources'][1], {u'last_modified': [u'Date format incorrect']})

    def test_package_update_delete_last_extra(self):
        old_fixture_data = {
            'name': self.package_fixture_data['name'],
            'extras': {
                u'key1': u'val1',
            },
        }
        new_fixture_data = {
            'name':u'somethingnew',
            'extras': {
                u'key1': None,
                },
        }
        self.create_package_with_admin_user(old_fixture_data)
        offset = self.package_offset(old_fixture_data['name'])
        params = '%s=1' % self.dumps(new_fixture_data)
        res = self.app.post(offset, params=params, status=self.STATUS_200_OK,
                            extra_environ=self.admin_extra_environ)

        try:
            # Check the returned package is as expected
            pkg = self.loads(res.body)
            assert_equal(pkg['name'], new_fixture_data['name'])
            expected_extras = copy.deepcopy(new_fixture_data['extras'])
            del expected_extras['key1']
            assert_equal(pkg['extras'], expected_extras)

            # Check extra was deleted
            model.Session.remove()
            package = self.get_package_by_name(new_fixture_data['name'])
            # - title
            self.assert_equal(package.extras, {})
        finally:
            self.purge_package_by_name(new_fixture_data['name'])

    def test_package_update_do_not_delete_last_extra(self):
        old_fixture_data = {
            'name': self.package_fixture_data['name'],
            'extras': {
                u'key1': u'val1',
            },
        }
        new_fixture_data = {
            'name':u'somethingnew',
            'extras': {}, # no extras specified, but existing
                          # ones should be left alone
        }
        self.create_package_with_admin_user(old_fixture_data)
        offset = self.package_offset(old_fixture_data['name'])
        params = '%s=1' % self.dumps(new_fixture_data)
        res = self.app.post(offset, params=params, status=self.STATUS_200_OK,
                            extra_environ=self.admin_extra_environ)

        try:
            # Check the returned package is as expected
            pkg = self.loads(res.body)
            assert_equal(pkg['name'], new_fixture_data['name'])
            expected_extras = {u'key1': u'val1'} # should not be deleted
            assert_equal(pkg['extras'], expected_extras)

            # Check extra was not deleted
            model.Session.remove()
            package = self.get_package_by_name(new_fixture_data['name'])
            # - title
            assert len(package.extras) == 1, package.extras
        finally:
            self.purge_package_by_name(new_fixture_data['name'])

    def test_entity_update_readd_tag(self):
        name = self.package_fixture_data['name']
        old_fixture_data = {
            'name': name,
            'tags': ['tag 1.', 'tag2']
        }
        new_fixture_data = {
            'name': name,
            'tags': ['tag 1.']
        }
        self.create_package_with_admin_user(old_fixture_data)
        offset = self.package_offset(name)
        params = '%s=1' % self.dumps(new_fixture_data)
        res = self.app.post(offset, params=params, status=self.STATUS_200_OK,
                            extra_environ=self.admin_extra_environ)

        # Check the returned package is as expected
        pkg = self.loads(res.body)
        assert_equal(pkg['name'], new_fixture_data['name'])
        assert_equal(pkg['tags'], ['tag 1.'])

        package = self.get_package_by_name(new_fixture_data['name'])
        assert len(package.get_tags()) == 1, package.get_tags()

        # now reinstate the tag
        params = '%s=1' % self.dumps(old_fixture_data)
        res = self.app.post(offset, params=params, status=self.STATUS_200_OK,
                            extra_environ=self.admin_extra_environ)
        pkg = self.loads(res.body)
        assert_equal(pkg['tags'], ['tag 1.', 'tag2'])

    def test_entity_update_conflict(self):
        package1_name = self.package_fixture_data['name']
        package1_data = {'name': package1_name}
        package1 = self.create_package_with_admin_user(package1_data)
        package2_name = u'somethingnew'
        package2_data = {'name': package2_name}
        package2 = self.create_package_with_admin_user(package2_data)
        try:
            package1_offset = self.package_offset(package1_name)
            # trying to rename package 1 to package 2's name
            print package1_offset, package2_data
            self.post(package1_offset, package2_data, self.STATUS_409_CONFLICT, extra_environ=self.admin_extra_environ)
        finally:
            self.purge_package_by_name(package2_name)

    def test_entity_update_empty(self):
        package1_name = self.package_fixture_data['name']
        package1_data = {'name': package1_name}
        package1 = self.create_package_with_admin_user(package1_data)
        package2_data = '' # this is the error
        package1_offset = self.package_offset(package1_name)
        self.app.put(package1_offset, package2_data,
                     status=self.STATUS_400_BAD_REQUEST)

    def test_entity_update_indexerror(self):
        """
        Test that we can't update a package if Solr is down.
        """
        bad_solr_url = 'http://127.0.0.1/badsolrurl'
        original_settings = SolrSettings.get()[0]
        try:
            SolrSettings.init(bad_solr_url)

            assert_raises(
                search.SearchIndexError, self.assert_package_update_ok, 'name', 'post'
            )
        finally:
            SolrSettings.init(original_settings)

    def test_package_update_delete_resource(self):
        old_fixture_data = {
            'name': self.package_fixture_data['name'],
            'resources': [{
                u'url':u'http://blah.com/file2.xml',
                u'format':u'xml',
                u'description':u'Appendix 1',
                u'hash':u'def123',
                u'alt_url':u'alt123',
            },{
                u'url':u'http://blah.com/file3.xml',
                u'format':u'xml',
                u'description':u'Appenddic 2',
                u'hash':u'ghi123',
                u'alt_url':u'alt123',
            }],
        }
        new_fixture_data = {
            'name':u'somethingnew',
            'resources': [],
        }
        self.create_package_with_admin_user(old_fixture_data)
        offset = self.package_offset(old_fixture_data['name'])
        params = '%s=1' % self.dumps(new_fixture_data)
        res = self.app.post(offset, params=params, status=self.STATUS_200_OK,
                            extra_environ=self.admin_extra_environ)

        try:
            # Check the returned package is as expected
            pkg = self.loads(res.body)
            assert_equal(pkg['name'], new_fixture_data['name'])
            assert_equal(pkg['resources'], [])

            # Check resources were deleted
            model.Session.remove()
            package = self.get_package_by_name(new_fixture_data['name'])
            self.assert_equal(len(package.resources), 0)
        finally:
            self.purge_package_by_name(new_fixture_data['name'])

    def test_entity_delete_ok(self):
        # create a package with package_fixture_data
        if not self.get_package_by_name(self.package_fixture_data['name']):
            self.create_package(admins=[self.user], name=self.package_fixture_data['name'])
        assert self.get_package_by_name(self.package_fixture_data['name'])
        # delete it
        offset = self.package_offset(self.package_fixture_data['name'])
        res = self.app.delete(offset, status=self.STATUS_200_OK,
                              extra_environ=self.admin_extra_environ)
        package = self.get_package_by_name(self.package_fixture_data['name'])
        self.assert_equal(package.state, 'deleted')
        model.Session.remove()

    def test_entity_delete_ok_without_request_headers(self):
        # create a package with package_fixture_data
        if not self.get_package_by_name(self.package_fixture_data['name']):
            self.create_package(admins=[self.user], name=self.package_fixture_data['name'])
        assert self.get_package_by_name(self.package_fixture_data['name'])
        # delete it
        offset = self.package_offset(self.package_fixture_data['name'])
        res = self.delete_request(offset, status=self.STATUS_200_OK,
                                  extra_environ=self.admin_extra_environ)
        package = self.get_package_by_name(self.package_fixture_data['name'])
        self.assert_equal(package.state, 'deleted')
        model.Session.remove()

    def test_entity_delete_not_found(self):
        package_name = u'random_one'
        assert not model.Session.query(model.Package).filter_by(name=package_name).count()
        offset = self.offset('/rest/dataset/%s' % package_name)
        res = self.app.delete(offset, status=self.STATUS_404_NOT_FOUND,
                              extra_environ=self.admin_extra_environ)

    def test_package_revisions(self):
        # check original revision
        res = self.app.get(self.offset('/rest/dataset/%s/revisions' % 'annakarenina'))
        revisions = res.json
        assert len(revisions) == 1, len(revisions)
        expected_keys = set(('id', 'message', 'author', 'timestamp', 'approved_timestamp'))
        keys = set(revisions[0].keys())
        assert_equal(keys, expected_keys)

        # edit anna
        pkg = model.Package.by_name('annakarenina')
        model.repo.new_revision()
        pkg.title = 'Tolstoy'
        model.repo.commit_and_remove()

        # check new revision is there
        res = self.app.get(self.offset('/rest/dataset/%s/revisions' % 'annakarenina'))
        revisions = res.json
        assert len(revisions) == 2, len(revisions)

        # check ordering
        assert revisions[0]["timestamp"] > revisions[1]["timestamp"]

        # edit related extra
        pkg = model.Package.by_name('annakarenina')
        model.repo.new_revision()
        pkg.extras['genre'] = 'literary'
        model.repo.commit_and_remove()

        # check new revision is there
        res = self.app.get(self.offset('/rest/dataset/%s/revisions' % 'annakarenina'))
        revisions = res.json
        assert len(revisions) == 3, len(revisions)

    def test_create_private_package_with_no_organization(self):
        '''Test that private packages with no organization cannot be created.

        '''
        testsysadmin = model.User.by_name('testsysadmin')
        result = tests.call_action_api(self.app, 'package_create', name='test',
                private=True, apikey=testsysadmin.apikey, status=409)
        assert result == {'__type': 'Validation Error',
                'private': ["Datasets with no organization can't be private."]}

    def test_create_public_package_with_no_organization(self):
        '''Test that public packages with no organization can be created.'''
        testsysadmin = model.User.by_name('testsysadmin')
        tests.call_action_api(self.app, 'package_create', name='test',
                private=False, apikey=testsysadmin.apikey)

    def test_make_package_with_no_organization_private(self):
        '''Test that private packages with no organization cannot be created
        by package_update.

        '''
        testsysadmin = model.User.by_name('testsysadmin')
        package = tests.call_action_api(self.app, 'package_create',
                name='test_2', private=False, apikey=testsysadmin.apikey)
        package['private'] = True
        result = tests.call_action_api(self.app, 'package_update',
                apikey=testsysadmin.apikey, status=409, **package)
        assert result == {'__type': 'Validation Error',
                'private': ["Datasets with no organization can't be private."]}


class TestPackagesVersion1(Version1TestCase, PackagesTestCase):
    def test_06_create_pkg_using_download_url(self):
        test_params = {
            'name':u'testpkg06',
            'download_url':u'ftp://ftp.monash.edu.au/pub/nihongo/JMdict.gz',
            }
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(test_params)
        res = self.app.post(offset, params=postparams,
                            extra_environ=self.admin_extra_environ)
        model.Session.remove()
        pkg = self.get_package_by_name(test_params['name'])
        assert pkg
        assert pkg.name == test_params['name'], pkg
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url == test_params['download_url'], pkg.resources[0]

    def test_10_edit_pkg_with_download_url(self):
        test_params = {
            'name':u'testpkg10',
            'download_url':u'testurl',
            }
        rev = model.repo.new_revision()
        pkg = model.Package()
        model.Session.add(pkg)
        pkg.name = test_params['name']
        pkg.download_url = test_params['download_url']
        model.Session.commit()

        pkg = self.get_package_by_name(test_params['name'])
        model.setup_default_user_roles(pkg, [self.user])
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()
        assert self.get_package_by_name(test_params['name'])

        # edit it
        pkg_vals = {'download_url':u'newurl'}
        offset = self.package_offset(test_params['name'])
        postparams = '%s=1' % self.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.admin_extra_environ)
        model.Session.remove()
        pkg = model.Session.query(model.Package).filter_by(name=test_params['name']).one()
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url == pkg_vals['download_url']

class TestPackagesVersion2(Version2TestCase, PackagesTestCase): pass
