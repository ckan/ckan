from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase 
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase 
from ckan.tests.functional.api.base import ApiUnversionedTestCase as UnversionedTestCase 

# Todo: Remove this ckan.model stuff.
import ckan.model as model


class PackagesTestCase(BaseModelApiTestCase):

    commit_changesets = False
    require_common_fixtures = True
    reuse_common_fixtures = True
    has_common_fixtures = False

    def setup(self):
        self.conditional_create_common_fixtures()
        self.init_extra_environ()

    def teardown(self):
        self.purge_package_by_name(self.testpackagevalues['name'])
        self.purge_package_by_name(u'somethingnew')
        self.reuse_or_delete_common_fixtures()

    def purge_package_by_name(self, package_name):
        package = self.get_package_by_name(package_name)
        if package:
            package.purge()
            self.commit_remove()

    def test_register_get_ok(self):
        offset = self.package_offset()
        res = self.app.get(offset, status=self.STATUS_200_OK)
        assert self.ref_package(self.anna) in res, res
        assert self.ref_package(self.war) in res, res

    def test_register_post_ok(self):
        assert not self.get_package_by_name(self.testpackagevalues['name'])
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=self.STATUS_200_OK,
                extra_environ=self.extra_environ)
        # Check the value of the Location header.
        location = res.header('Location')
        assert offset in location
        res = self.app.get(location, status=self.STATUS_200_OK)
        # Check the database record.
        self.remove()
        pkg = self.get_package_by_name(self.testpackagevalues['name'])
        assert pkg
        self.assert_equal(pkg.title, self.testpackagevalues['title'])
        self.assert_equal(pkg.url, self.testpackagevalues['url'])
        self.assert_equal(pkg.license_id, self.testpackage_license_id)
        self.assert_equal(len(pkg.tags), 2)
        self.assert_equal(len(pkg.extras), 2)
        for key, value in self.testpackagevalues['extras'].items():
            self.assert_equal(pkg.extras[key], value)
        self.assert_equal(len(pkg.resources), len(self.testpackagevalues['resources']))
        for (i, expected_resource) in enumerate(self.testpackagevalues['resources']):
            package_resource = pkg.resources[i]
            for key in expected_resource.keys():
                package_resource_value = getattr(package_resource, key)
                expected_resource_value = expected_resource[key]
                self.assert_equal(package_resource_value, expected_resource_value)

        # Test Package Entity Get 200.
        offset = self.package_offset(self.testpackagevalues['name'])
        res = self.app.get(offset, status=self.STATUS_200_OK)
        # Todo: Instead loads() the data and then check actual values.
        assert self.testpackagevalues['name'] in res, res
        assert '"license_id": "%s"' % self.testpackagevalues['license_id'] in res, res
        assert self.testpackagevalues['tags'][0] in res, res
        assert self.testpackagevalues['tags'][1] in res, res
        assert '"extras": {' in res, res
        for key, value in self.testpackagevalues['extras'].items():
            assert '"%s": "%s"' % (key, value) in res, res
        
        self.remove()
        
        # Test Packages Register Post 409 (conflict - create duplicate package).
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=[409],
                extra_environ=self.extra_environ)
        self.remove()

    def test_register_post_bad_request(self):
        test_params = {
            'name':u'testpkg06_400',
            'resources':[u'should_be_a_dict'],
        }
        offset = self.offset('/rest/package')
        postparams = '%s=1' % self.dumps(test_params)
        res = self.app.post(offset, params=postparams, status=[400],
                extra_environ=self.extra_environ)

    def test_register_post_jsonp_bad_request(self):
        # JSONP callback should only work for GETs, not POSTs.
        pkg_name = u'test6jsonp'
        assert not self.get_package_by_name(pkg_name)
        offset = self.offset('/rest/package?callback=jsoncallback')
        postparams = '%s=1' % self.dumps({'name': pkg_name})
        res = self.app.post(offset, params=postparams, status=[400],
                            extra_environ=self.extra_environ)

    def test_register_post_denied(self):
        offset = self.offset('/rest/package')
        postparams = '%s=1' % self.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=self.STATUS_403_ACCESS_DENIED)

    def test_entity_get_ok(self):
        package_refs = [self.anna.name, self.anna.id]
        for ref in package_refs:
            offset = self.offset('/rest/package/%s' % ref)
            res = self.app.get(offset, status=self.STATUS_200_OK)
            self.assert_msg_represents_anna(msg=res.body)

    def test_entity_get_ok_jsonp(self):
        offset = self.anna_offset(postfix='?callback=jsoncallback')
        res = self.app.get(offset, status=200)
        import re
        assert re.match('jsoncallback\(.*\);', res.body), res
        # Unwrap JSONP callback (we want to look at the data).
        msg = res.body[len('jsoncallback')+1:-2]
        self.assert_msg_represents_anna(msg=msg)

    def test_entity_get_not_found(self):
        # Don't use package_offset('22222') because there isn't a '22222'.
        offset = self.offset('/rest/package/22222')
        res = self.app.get(offset, status=404)
        self.remove()

# Todo: Remove this test, it repeats the test above.
#    def test_entity_get_not_found(self):
#        pkg_name = u'random_one'
#        assert not model.Session.query(model.Package).filter_by(name=pkg_name).count()
#        offset = self.package_offset(pkg_name)
#        res = self.app.get(offset, status=404)
#        self.remove()

    def test_entity_update_denied(self):
        offset = self.anna_offset()
        postparams = '%s=1' % self.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=self.STATUS_403_ACCESS_DENIED)

    def test_entity_delete_denied(self):
        offset = self.anna_offset()
        res = self.app.delete(offset, status=self.STATUS_403_ACCESS_DENIED)

    #def test_09_update_package_entity_not_found(self):
    #    # Don't use package_offset('22222') because there isn't a '22222'.
    #    offset = self.offset('/rest/package/22222')
    #    postparams = '%s=1' % self.dumps(self.testpackagevalues)
    #    res = self.app.post(offset, params=postparams, status=[404],
    #           extra_environ=self.extra_environ)
    #    self.remove()

    def assert_package_update_ok(self, pkg_ref_attribute):
        # Test Packages Entity Put 200.

        # create a package with testpackagevalues
        tag_names = [u'tag1', u'tag2', u'tag3']
        #test_pkg_dict = {'name':u'test_10_edit_pkg',
        test_pkg_dict = {'name':self.testpackagevalues['name'],
                         'url':self.testpackagevalues['url'],
                         'tags':tag_names,
                         'extras':{u'key1':u'val1', u'key2':u'val2'},
                         'admins':[self.user.name],
                         }
        self.create_package(**test_pkg_dict)
        pkg = self.get_package_by_name(test_pkg_dict['name'])
        model.setup_default_user_roles(pkg, [self.user])
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        # edit it
        edited_pkg_dict = {
            'name':u'somethingnew',
            'title':u'newtesttitle',
            'resources': [
                {
                    u'url':u'http://blah.com/file2.xml',
                    u'format':u'xml',
                    u'description':u'Appendix 1',
                    u'hash':u'def123',
                },
                {
                    u'url':u'http://blah.com/file3.xml',
                    u'format':u'xml',
                    u'description':u'Appenddic 2',
                    u'hash':u'ghi123',
                },
            ],
            'extras':{u'key3':u'val3', u'key2':None},
            'tags':[u'tag1', u'tag2', u'tag4', u'tag5'],
        }
        offset = self.package_offset(test_pkg_dict['name'])
        postparams = '%s=1' % self.dumps(edited_pkg_dict)
        res = self.app.post(offset, params=postparams, status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)

        # Check submitted field have changed.
        model.Session.remove()
        pkg = model.Session.query(model.Package).filter_by(name=edited_pkg_dict['name']).one()
        # - title
        assert pkg.title == edited_pkg_dict['title']
        # - tags
        pkg_tagnames = [tag.name for tag in pkg.tags]
        for tagname in edited_pkg_dict['tags']:
            assert tagname in pkg_tagnames, 'tag %r not in %r' % (tagname, pkg_tagnames)
        # - resources
        assert len(pkg.resources), "Package has no resources: %s" % pkg
        assert len(pkg.resources) == 2, len(pkg.resources)
        resource = pkg.resources[0]
        assert resource.url == u'http://blah.com/file2.xml', resource.url
        assert resource.format == u'xml', resource.format
        assert resource.description == u'Appendix 1', resource.description
        assert resource.hash == u'def123', resource.hash
        resource = pkg.resources[1]
        assert resource.url == 'http://blah.com/file3.xml', resource.url
        assert resource.format == u'xml', resource.format
        assert resource.description == u'Appenddic 2', resource.description
        assert resource.hash == u'ghi123', resource.hash

        # Check unsubmitted fields have not changed.
        # - url
        assert pkg.url == self.testpackagevalues['url'], pkg.url
        # - extras
        assert len(pkg.extras) == 2, pkg.extras
        for key, value in {u'key1':u'val1', u'key3':u'val3'}.items():
            assert pkg.extras[key] == value, pkg.extras

    def test_package_update_ok_by_id(self):
        self.assert_package_update_ok('id')

    def test_entity_update_ok_by_name(self):
        self.assert_package_update_ok('name')

    def test_entity_update_conflict(self):
        # create a package with testpackagevalues
        if not self.get_package_by_name(self.testpackagevalues['name']):
            pkg = model.Package()
            model.Session.add(pkg)
            pkg.name = self.testpackagevalues['name']
            rev = model.repo.new_revision()
            model.Session.commit()

            pkg = self.get_package_by_name(self.testpackagevalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert self.get_package_by_name(self.testpackagevalues['name'])
        
        # create a package with name 'dupname'
        dupname = u'dupname'
        if not self.get_package_by_name(dupname):
            pkg = model.Package()
            model.Session.add(pkg)
            pkg.name = dupname
            rev = model.repo.new_revision()
            model.Session.commit()
        assert self.get_package_by_name(dupname)

        # edit first package to have dupname
        pkg_vals = {'name':dupname}
        offset = self.package_offset(self.testpackagevalues['name'])
        postparams = '%s=1' % self.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.extra_environ)
        model.Session.remove()

    def test_entity_delete_ok(self):
        # create a package with testpackagevalues
        if not self.get_package_by_name(self.testpackagevalues['name']):
            pkg = model.Package()
            model.Session.add(pkg)
            pkg.name = self.testpackagevalues['name']
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()

            pkg = self.get_package_by_name(self.testpackagevalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert self.get_package_by_name(self.testpackagevalues['name'])

        # delete it
        offset = self.package_offset(self.testpackagevalues['name'])
        res = self.app.delete(offset, status=self.STATUS_200_OK,
                extra_environ=self.extra_environ)
        pkg = self.get_package_by_name(self.testpackagevalues['name'])
        assert pkg.state == 'deleted'
        model.Session.remove()

    def test_entity_delete_not_found(self):
        pkg_name = u'random_one'
        assert not model.Session.query(model.Package).filter_by(name=pkg_name).count()
        offset = self.offset('/rest/package/%s' % pkg_name)
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)


class TestPackagesVersion1(Version1TestCase, PackagesTestCase): pass
class TestPackagesVersion2(Version2TestCase, PackagesTestCase): pass
class TestPackagesUnversioned(UnversionedTestCase, PackagesTestCase): pass

