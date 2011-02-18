from sqlalchemy import MetaData, __version__ as sqav
from nose.tools import assert_equal, raises

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

class TestResource:
    def setup(self):
        model.repo.init_db()
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
        rg = pkg.resource_groups[0]
        for url in self.urls:
            pr = model.Resource(url=url,
                                format=self.format,
                                description=self.description,
                                hash=self.hash,
                                alt_url=self.alt_url,
                                extras={u'size':self.size},
                                )
            rg.resources.append(pr)
            pkg.resource_groups.append(rg)
        model.repo.commit_and_remove()

    def teardown(self):
        model.repo.delete_all()
        
    def test_01_create_package_resources(self):

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resource_groups) == 1
        assert len(pkg.resource_groups[0].resources) == len(self.urls), pkg.resource_groups[0].resources

        resource_group_0 = pkg.resource_groups[0]
        assert resource_group_0.label == 'default', resource_group_0
        assert resource_group_0.sort_order == '' , resource_group_0

        resource_0 = resource_group_0.resources[0]

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


    def test_02_delete_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups[0]
        res = rg.resources[0]
        assert len(rg.resources) == 2, rg.resources
        rev = model.repo.new_revision()
        res.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups[0]
        assert len(rg.resources) == 1, rg.resources
        assert len(rg.resources_all) == 2, rg.resources_all
    
    def test_03_reorder_resources(self):
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups[0]

        res0 = rg.resources[0]
        del rg.resources[0]
        rg.resources.append(res0)
        # this assert will fail
        # assert pkg.resources[1].position == 1
        # Why? According to docs for ordering list it does not reorder appended
        # elements by default (see
        # http://www.sqlalchemy.org/trac/browser/lib/sqlalchemy/ext/orderinglist.py#L197)
        # so we have to call reorder directly in supported versions
        # of sqlalchemy and set position to None in older ones.
        if sqav.startswith('0.4'):
            rg.resources[1].position = None
        else:
            rg.resources.target.reorder()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(rg.resources) == 2, rg.resources
        lastres = rg.resources[1]
        assert lastres.position == 1, lastres
        assert lastres.url == self.urls[0]
        

    def test_04_insert_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        rev = model.repo.new_revision()
        newurl = u'http://xxxxxxxxxxxxxxx'

        resource = model.Resource(url=newurl)
        rg = pkg.resource_groups[0]

        rg.resources.insert(0, resource)
        model.repo.commit_and_remove()

        rg = model.Package.by_name(self.pkgname).resource_groups[0]
        assert len(rg.resources) == 3, rg.resources
        assert rg.resources[1].url == self.urls[0]
        assert len(rg.resources[1].all_revisions) == 2

    def test_05_delete_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource)
        active_resources = model.Session.query(model.Resource).\
                           filter_by(state=model.State.ACTIVE)
        assert all_resources.count() == 2, all_resources.all()
        assert active_resources.count() == 2, active_resources.all()
        rev = model.repo.new_revision()
        pkg.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        # OK for resources remain active
        assert all_resources.count() == 2, all_resources.all()
        assert active_resources.count() == 2, active_resources.all()

    @raises(AssertionError)
    def test_06_not_allow_two_resource_groups(self):
        pkg = model.Package.by_name(self.pkgname)
        resource_group = model.ResourceGroup(label="new")
        pkg.resource_groups.append(resource_group)
        pkg.resources

    def test_07_purge_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource).all()
        assert len(all_resources) == 2, pkg.resources
        rev = model.repo.new_revision()
        pkg.purge()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource).\
                        filter_by(state=model.State.ACTIVE).all()
        assert len(all_resources) == 0, pkg.resources


class TestResourceEdit:
    @classmethod
    def setup(self):
        model.repo.init_db()
        self.pkgname = u'geodata'
        self.urls = [u'http://somewhere.com/',
                     u'http://elsewhere.com/',
                     u'http://third.com']
        self.format = u'csv'
        self.description = u'Important part.'
        self.hash = u'abc123'
        rev = model.repo.new_revision()
        self.pkg = model.Package(name=self.pkgname)
        model.Session.add(self.pkg)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        rev = model.repo.new_revision()

        rg = pkg.resource_groups[0]
        for url in self.urls:
            rg.resources.append(model.Resource(url=url,
                                       format=self.format,
                                       description=self.description,
                                       hash=self.hash))
        model.repo.commit_and_remove()

    @classmethod
    def teardown(self):
        model.Session.remove()
        model.repo.rebuild_db()


    def test_1_update_resources_no_ids(self):
        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups[0]
        offset = len(self.urls)
        assert len(rg.resources) == offset, rg.resources
        original_res_ids = [res.id for res in rg.resources]
        def print_resources(caption, resources):
            print caption, '\n'.join(['<url=%s format=%s>' % (res.url, res.format) for res in resources])
        print_resources('BEFORE', rg.resources)
        
        rev = model.repo.new_revision()
        res_dicts = [
            { #unchanged
                'url':self.urls[0], 'format':self.format,
                'description':self.description, 'hash':self.hash},
            { #slightly different
                'url':self.urls[1], 'format':u'OTHER FORMAT',
                'description':self.description, 'hash':self.hash},
            ]
        pkg.update_resources(res_dicts)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        rg = pkg.resource_groups[0]
        print_resources('AFTER', rg.resources)
        assert len(rg.resources) == len(res_dicts), rg.resources
        for i, res in enumerate(pkg.resources):
            assert res.url == res_dicts[i]['url']
            assert res.format == res_dicts[i]['format']
        assert_equal(pkg.resources[0].id,  original_res_ids[0])
        assert pkg.resources[1].id != original_res_ids[1]

        # package resource revisions
        prr_q = model.Session.query(model.ResourceRevision)
        assert len(prr_q.all()) == offset + 2 + 1, prr_q.all() # 2 deletions, 1 new one
        prr1 = prr_q.\
               filter_by(revision_id=rev.id).\
               order_by(model.resource_revision_table.c.position).\
               filter_by(state=model.State.ACTIVE).one()
        assert prr1.resource_group == rg, prr1.resource_group
        assert prr1.url == self.urls[1], '%s != %s' % (prr1.url, self.urls[1])
        assert prr1.revision.id == rev.id, '%s != %s' % (prr1.revision.id, rev.id)
        # revision contains package resource revisions
        rev_prrs = model.repo.list_changes(rev)[model.Resource]
        assert len(rev_prrs) == 3, rev_prrs # 2 deleted, 1 new

        # previous revision still contains previous ones
        previous_rev = model.repo.history()[1]
        previous_rev_prrs = model.repo.list_changes(previous_rev)[model.Resource]
        assert len(previous_rev_prrs) == offset, rev_prrs

    def test_2_update_resources_with_ids(self):
        pkg = model.Package.by_name(self.pkgname)
        offset = len(self.urls)
        assert len(pkg.resources) == offset, pkg.resources
        original_res_ids = [res.id for res in pkg.resources]
        def print_resources(caption, resources):
            print caption, '\n'.join(['<url=%s format=%s>' % (res.url, res.format) for res in resources])
        print_resources('BEFORE', pkg.resources)
        
        rev = model.repo.new_revision()
        res_dicts = [
            { #unchanged
                'url':self.urls[0], 'format':self.format,
                'description':self.description, 'hash':self.hash,
                'id':original_res_ids[0]},
            { #id from res 2, but url from res 1
                'url':self.urls[1], 'format':u'OTHER FORMAT',
                'description':self.description, 'hash':self.hash,
                'id':original_res_ids[2]},
            ]
        pkg.update_resources(res_dicts)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        print_resources('AFTER', pkg.resources)
        assert len(pkg.resources) == len(res_dicts), pkg.resources
        for i, res in enumerate(pkg.resources):
            assert res.url == res_dicts[i]['url']
            assert res.format == res_dicts[i]['format']
        assert pkg.resources[0].id == original_res_ids[0]
        assert pkg.resources[1].id == original_res_ids[2]

