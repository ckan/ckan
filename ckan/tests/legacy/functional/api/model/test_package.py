# encoding: utf-8

from __future__ import print_function

import copy

from nose.tools import assert_equal, assert_raises

from ckan.lib.create_test_data import CreateTestData
import ckan.lib.search as search
from ckan.lib.search.common import SolrSettings

from ckan.tests.legacy.functional.api.base import BaseModelApiTestCase

import ckan.tests.legacy as tests

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

    def test_register_post_indexerror(self):
        """
        Test that we can't add a package if Solr is down.
        """
        bad_solr_url = 'http://example.com/badsolrurl'
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

    def test_entity_get_ok_jsonp(self):
        offset = self.anna_offset(postfix='?callback=jsoncallback')
        res = self.app.get(offset, status=self.STATUS_200_OK)
        import re
        assert re.match('jsoncallback\(.*\);', res.body), res
        # Unwrap JSONP callback (we want to look at the data).
        msg = res.body[len('jsoncallback')+1:-2]
        self.assert_msg_represents_anna(msg=msg)

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

    def create_package_with_admin_user(self, package_data):
        '''Creates a package with self.user as admin and provided package_data.
        '''
        self.create_package(data=package_data)

    def test_package_update_ok_by_id(self):
        self.assert_package_update_ok('id', 'post')

    def test_entity_update_ok_by_name(self):
        self.assert_package_update_ok('name', 'post')

    def test_package_update_ok_by_id_by_put(self):
        self.assert_package_update_ok('id', 'put')

    def test_entity_update_ok_by_name_by_put(self):
        self.assert_package_update_ok('name', 'put')

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
            print(package1_offset, package2_data)
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
        bad_solr_url = 'http://example.com/badsolrurl'
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
                u'format':u'XML',
                u'description':u'Appendix 1',
                u'hash':u'def123',
                u'alt_url':u'alt123',
            },{
                u'url':u'http://blah.com/file3.xml',
                u'format':u'XML',
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
            self.create_package(name=self.package_fixture_data['name'])
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
            self.create_package(name=self.package_fixture_data['name'])
        assert self.get_package_by_name(self.package_fixture_data['name'])
        # delete it
        offset = self.package_offset(self.package_fixture_data['name'])
        res = self.delete_request(offset, status=self.STATUS_200_OK,
                                  extra_environ=self.admin_extra_environ)
        package = self.get_package_by_name(self.package_fixture_data['name'])
        self.assert_equal(package.state, 'deleted')
        model.Session.remove()

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
