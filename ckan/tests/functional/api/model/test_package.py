from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase 
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase 
from ckan.tests.functional.api.base import ApiUnversionedTestCase as UnversionedTestCase 

# Todo: Remove this ckan.model stuff.
import ckan.model as model

class PackagesTestCase(BaseModelApiTestCase):

    commit_changesets = False
    reuse_common_fixtures = True

    def setup(self):
        model.Session.remove()
        model.repo.init_db()
        super(PackagesTestCase, self).setup()
        # XXX check super.setup for if any dupes there

    def teardown(self):
        self.purge_package_by_name(self.package_fixture_data['name'])
        self.purge_package_by_name(u'somethingnew')
        super(PackagesTestCase, self).teardown()
        model.Session.connection().invalidate()

    def test_register_get_ok(self):
        offset = self.package_offset()
        res = self.app.get(offset, status=self.STATUS_200_OK)
        assert self.ref_package(self.anna) in res, res
        assert self.ref_package(self.war) in res, res

    def test_register_post_ok(self):
        assert not self.get_package_by_name(self.package_fixture_data['name'])
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams, status=self.STATUS_200_OK,
                extra_environ=self.extra_environ)
        # Check the value of the Location header.
        location = res.header('Location')
        assert offset in location
        res = self.app.get(location, status=self.STATUS_200_OK)
        # Check the database record.
        self.remove()
        package = self.get_package_by_name(self.package_fixture_data['name'])
        assert package
        self.assert_equal(package.title, self.package_fixture_data['title'])
        self.assert_equal(package.url, self.package_fixture_data['url'])
        self.assert_equal(package.license_id, self.testpackage_license_id)
        self.assert_equal(len(package.tags), 2)
        self.assert_equal(len(package.extras), 2)
        for key, value in self.package_fixture_data['extras'].items():
            self.assert_equal(package.extras[key], value)
        self.assert_equal(len(package.resources), len(self.package_fixture_data['resources']))
        for (i, expected_resource) in enumerate(self.package_fixture_data['resources']):
            package_resource = package.resources[i]
            for key in expected_resource.keys():
                package_resource_value = getattr(package_resource, key)
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
        
        self.remove()
        
        # Test Packages Register Post 409 (conflict - create duplicate package).
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams, status=self.STATUS_409_CONFLICT,
                extra_environ=self.extra_environ)
        self.remove()

    def test_register_post_bad_request(self):
        test_params = {
            'name':u'testpackage06_400',
            'resources':[u'should_be_a_dict'],
        }
        offset = self.offset('/rest/package')
        postparams = '%s=1' % self.dumps(test_params)
        res = self.app.post(offset, params=postparams, status=self.STATUS_400_BAD_REQUEST,
                extra_environ=self.extra_environ)

    def test_register_post_denied(self):
        offset = self.offset('/rest/package')
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams, status=self.STATUS_403_ACCESS_DENIED)

    def test_entity_get_ok(self):
        package_refs = [self.anna.name, self.anna.id]
        for ref in package_refs:
            offset = self.offset('/rest/package/%s' % ref)
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
        # Don't use package_offset('22222') because there isn't a '22222'.
        offset = self.offset('/rest/package/22222')
        res = self.app.get(offset, status=self.STATUS_404_NOT_FOUND)
        self.remove()

    def test_entity_update_denied(self):
        offset = self.anna_offset()
        postparams = '%s=1' % self.dumps(self.package_fixture_data)
        res = self.app.post(offset, params=postparams, status=self.STATUS_403_ACCESS_DENIED)

    def test_entity_delete_denied(self):
        offset = self.anna_offset()
        res = self.app.delete(offset, status=self.STATUS_403_ACCESS_DENIED)

    #def test_09_update_package_entity_not_found(self):
    #    # Don't use package_offset('22222') because there isn't a '22222'.
    #    offset = self.offset('/rest/package/22222')
    #    postparams = '%s=1' % self.dumps(self.package_fixture_data)
    #    res = self.app.post(offset, params=postparams, status=[404],
    #           extra_environ=self.extra_environ)
    #    self.remove()

    def create_package_roles_revision(self, package_data):
        self.create_package(admins=[self.user], data=package_data)

    def assert_package_update_ok(self, package_ref_attribute):
        old_fixture_data = {
            'name': self.package_fixture_data['name'],
            'url': self.package_fixture_data['url'],
            'tags': [u'tag1', u'tag2', u'tag3'],
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
            },{
                u'url':u'http://blah.com/file3.xml',
                u'format':u'xml',
                u'description':u'Appenddic 2',
                u'hash':u'ghi123',
            }],
            'extras': {
                u'key3': u'val3', 
                u'key2': None
             },
            'tags': [u'tag1', u'tag2', u'tag4', u'tag5'],
        }
        self.create_package_roles_revision(old_fixture_data)
        offset = self.package_offset(old_fixture_data['name'])
        params = '%s=1' % self.dumps(new_fixture_data)
        res = self.app.post(offset, params=params, status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)

        # Check submitted field have changed.
        self.remove()
        package = self.get_package_by_name(new_fixture_data['name'])
        # - title
        self.assert_equal(package.title, new_fixture_data['title'])
        # - tags
        package_tagnames = [tag.name for tag in package.tags]
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
        resource = package.resources[1]
        self.assert_equal(resource.url, 'http://blah.com/file3.xml')
        self.assert_equal(resource.format, u'xml')
        self.assert_equal(resource.description, u'Appenddic 2')
        self.assert_equal(resource.hash, u'ghi123')

        # Check unsubmitted fields have not changed.
        # - url
        self.assert_equal(package.url, self.package_fixture_data['url'])
        # - extras
        self.assert_equal(len(package.extras), 2)
        for key, value in {u'key1':u'val1', u'key3':u'val3'}.items():
            self.assert_equal(package.extras[key], value)
        # Todo: Something about the fact that extras are not unsubmitted!
        # Todo: Check what happens to key2.
        # Todo: Figure out why key2 is set to None - do we need a test for key2 not existing.

    def test_package_update_ok_by_id(self):
        self.assert_package_update_ok('id')

    def test_entity_update_ok_by_name(self):
        self.assert_package_update_ok('name')

    def test_entity_update_conflict(self):
        package1_name = self.package_fixture_data['name']
        package1_data = {'name': package1_name}
        package1 = self.create_package_roles_revision(package1_data)
        package2_name = u'somethingnew'
        package2_data = {'name': package2_name}
        package2 = self.create_package_roles_revision(package2_data)
        package1_offset = self.package_offset(package1_name)
        self.post(package1_offset, package2_data, self.STATUS_409_CONFLICT)

    def test_entity_delete_ok(self):
        # create a package with package_fixture_data
        if not self.get_package_by_name(self.package_fixture_data['name']):
            rev = model.repo.new_revision()
            package = model.Package()
            model.Session.add(package)
            package.name = self.package_fixture_data['name']
            model.repo.commit_and_remove()

            package = self.get_package_by_name(self.package_fixture_data['name'])
            model.setup_default_user_roles(package, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert self.get_package_by_name(self.package_fixture_data['name'])

        # delete it
        offset = self.package_offset(self.package_fixture_data['name'])
        res = self.app.delete(offset, status=self.STATUS_200_OK,
                extra_environ=self.extra_environ)
        package = self.get_package_by_name(self.package_fixture_data['name'])
        self.assert_equal(package.state, 'deleted')
        model.Session.remove()

    def test_entity_delete_not_found(self):
        package_name = u'random_one'
        assert not model.Session.query(model.Package).filter_by(name=package_name).count()
        offset = self.offset('/rest/package/%s' % package_name)
        res = self.app.delete(offset, status=self.STATUS_404_NOT_FOUND,
                              extra_environ=self.extra_environ)


class TestPackagesVersion1(Version1TestCase, PackagesTestCase): pass
class TestPackagesVersion2(Version2TestCase, PackagesTestCase): pass
class TestPackagesUnversioned(UnversionedTestCase, PackagesTestCase): pass

