from sqlalchemy import MetaData, __version__ as sqav
from nose.tools import assert_equal, raises

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData


class TestResource:
    def setup(self):
        self.pkgname = u'resourcetest'
        assert not model.Package.by_name(self.pkgname)
        assert model.Session.query(model.Resource).count() == 0
        self.urls = [u'http://somewhere.com/', u'http://elsewhere.com/']
        self.format = u'csv'
        self.description = u'Important part.'
        self.hash = u'abc123'
        self.alt_url = u'http://alturl' 
        self.size = 200
        self.label = 'labeltest'
        self.sort_order = '1'
        rev = model.repo.new_revision()
        pkg = model.Package(name=self.pkgname)
        model.Session.add(pkg)
        rg = pkg.resource_groups_all[0]
        for url in self.urls:
            pr = model.Resource(url=url,
                                format=self.format,
                                description=self.description,
                                hash=self.hash,
                                alt_url=self.alt_url,
                                extras={u'size':self.size},
                                )
            rg.resources_all.append(pr)
        pr = model.Resource(url="no_extra",
                            format=self.format,
                            description=self.description,
                            hash=self.hash,
                            )
        rg.resources_all.append(pr)
        model.repo.commit_and_remove()

    def teardown(self):
        model.repo.rebuild_db()
        
    def test_01_create_package_resources(self):

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resource_groups_all) == 1
        assert len(pkg.resource_groups_all[0].resources_all) == 3, pkg.resource_groups_all[0].resources

        resource_group_0 = pkg.resource_groups_all[0]
        assert resource_group_0.label == 'default', resource_group_0
        assert resource_group_0.sort_order == '' , resource_group_0

        resource_0 = resource_group_0.resources_all[0]

        assert resource_0.url == self.urls[0], resource_0
        assert resource_0.description == self.description, resource_0
        assert resource_0.hash == self.hash, resource_0
        assert resource_0.position == 0, resource_0.position
        assert resource_0.alt_url == self.alt_url, resource_0.alt_url
        assert_equal(resource_0.extras[u'size'], self.size)

        assert resource_group_0.package == pkg, resource_group_0.package
        assert resource_0.resource_group == resource_group_0, resource.resource_group

        generated_dict_resource = resource_0.as_dict()
        assert generated_dict_resource['alt_url'] == u'http://alturl', generated_dict_resource['alt_url']
        assert_equal(generated_dict_resource['size'], 200)

        generated_dict_resource_group = resource_group_0.as_dict()
        assert generated_dict_resource_group['label'] == 'default', generated_dict_resource_group['label']

        ## check to see if extra descriptor deletes properly
        rev = model.repo.new_revision()
        del resource_0.extras[u'size']
        assert resource_0.extras == {u'alt_url': u'http://alturl'}, pkg.resources[0].extras

        del resource_0.alt_url
        assert resource_0.extras == {}, pkg.resources[0].extras
        assert resource_0.alt_url is None

        resource_0.alt_url = 'weeee'
        assert resource_0.extras == {u'alt_url': u'weeee'}, resource_0.extras

        model.Session.add(resource_0)

        model.repo.commit_and_remove()
        pkg = model.Package.by_name(self.pkgname)

        assert resource_0.extras == {u'alt_url': u'weeee'}, resource_0.extras
        assert resource_0.alt_url == 'weeee', resource_0.alt_url

        pkg = model.Package.by_name(self.pkgname)

        assert pkg.resources[2].extras == {}, pkg.resources[2].extras


    def test_02_delete_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups_all[0]
        res = rg.package.resources[0]
        assert len(rg.package.resources) == 3, rg.resources
        rev = model.repo.new_revision()
        res.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups_all[0]
        assert len(rg.package.resources) == 2, rg.resources
        assert len(rg.resources_all) == 3, rg.resources_all
    
    def test_03_reorder_resources(self):
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups_all[0]

        res0 = rg.resources_all[0]
        del rg.resources_all[0]
        rg.resources_all.append(res0)
        # this assert will fail
        # assert pkg.resources[1].position == 1
        # Why? According to docs for ordering list it does not reorder appended
        # elements by default (see
        # http://www.sqlalchemy.org/trac/browser/lib/sqlalchemy/ext/orderinglist.py#L197)
        # so we have to call reorder directly in supported versions
        # of sqlalchemy and set position to None in older ones.
        rg.resources_all.reorder()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(rg.resources_all) == 3, len(rg.package.resources)
        lastres = rg.package.resources[2]
        assert lastres.position == 2, lastres
        print lastres
        assert lastres.url == self.urls[0], (self.urls, lastres.url)
        

    def test_04_insert_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        rev = model.repo.new_revision()
        newurl = u'http://xxxxxxxxxxxxxxx'

        resource = model.Resource(url=newurl)
        rg = pkg.resource_groups_all[0]

        rg.resources_all.insert(0, resource)
        model.repo.commit_and_remove()

        rg = model.Package.by_name(self.pkgname).resource_groups_all[0]
        assert len(rg.package.resources) == 4, rg.resources
        assert rg.resources_all[1].url == self.urls[0]
        assert len(rg.resources_all[1].all_revisions) == 2

    def test_05_delete_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource)
        active_resources = model.Session.query(model.Resource).\
                           filter_by(state=model.State.ACTIVE)
        assert all_resources.count() == 3, all_resources.all()
        assert active_resources.count() == 3, active_resources.count()
        rev = model.repo.new_revision()
        pkg.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        # OK for resources remain active
        assert all_resources.count() == 3, all_resources.all()
        assert active_resources.count() == 3, active_resources.count()

    @raises(AssertionError)
    def test_06_not_allow_two_resource_groups(self):
        pkg = model.Package.by_name(self.pkgname)
        resource_group = model.ResourceGroup(label="new")
        pkg.resource_groups_all.append(resource_group)
        pkg.resources

    def test_07_purge_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource).all()
        assert len(all_resources) == 3, pkg.resources
        rev = model.repo.new_revision()
        pkg.purge()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource).\
                        filter_by(state=model.State.ACTIVE).all()
        assert len(all_resources) == 0, pkg.resources


