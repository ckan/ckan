from sqlalchemy import MetaData, __version__ as sqav

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

class TestPackageResource:
    def setup(self):
        model.repo.init_db()
        self.pkgname = u'resourcetest'
        assert not model.Package.by_name(self.pkgname)
        assert model.Session.query(model.PackageResource).count() == 0
        self.urls = [u'http://somewhere.com/', u'http://elsewhere.com/']
        self.format = u'csv'
        self.description = u'Important part.'
        self.hash = u'abc123'
        self.alt_url = u'http://alturl' 
        self.size = 200
        rev = model.repo.new_revision()
        pkg = model.Package(name=self.pkgname)
        model.Session.add(pkg)
        for url in self.urls:
            pr = model.PackageResource(url=url,
                                       format=self.format,
                                       description=self.description,
                                       hash=self.hash,
                                       alt_url = self.alt_url,
                                       size = self.size,
                                       )
            pkg.resources.append(pr)
        model.repo.commit_and_remove()

    def teardown(self):
        model.Session.remove()
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        if pkg:
            model.Session().autoflush = False
            pkg.purge()
        model.repo.commit_and_remove()
        # XXX do we need above?
        model.repo.clean_db()
        
    def test_01_create_package_resources(self):
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == len(self.urls), pkg.resources
        assert pkg.resources[0].url == self.urls[0], pkg.resources[0]
        assert pkg.resources[0].description == self.description, pkg.resources[0]
        assert pkg.resources[0].hash == self.hash, pkg.resources[0]
        assert pkg.resources[0].position == 0, pkg.resources[0].position
        assert pkg.resources[0].alt_url == self.alt_url, pkg.resources[0].alt_url
        assert pkg.resources[0].size == unicode(self.size), pkg.resources[0].size

        resources = pkg.resources
        assert resources[0].package == pkg, resources[0].package

        generated_dict = pkg.resources[0].as_dict()
        assert generated_dict["alt_url"] == u'http://alturl', generated_dict["alt_url"]
        assert generated_dict["size"] == u'200', generated_dict["size"]

        ## check to see if extra info desriptor deletes properly
        rev = model.repo.new_revision()
        del pkg.resources[0].size
        assert pkg.resources[0].extra_info == {u'alt_url': u'http://alturl'}, pkg.resources[0].extra_info
        assert pkg.resources[0].size is None

        pkg.resources[0].alt_url = "weeee"
        assert pkg.resources[0].extra_info == {u'alt_url': u'weeee'}, pkg.resources[0].extra_info

        model.Session.add(pkg.resources[0])

        model.repo.commit_and_remove()
        pkg = model.Package.by_name(self.pkgname)

        assert pkg.resources[0].extra_info == {u'alt_url': u'weeee'}, pkg.resources[0].extra_info
        assert pkg.resources[0].alt_url == "weeee", pkg.resources[0].alt_url

    def test_02_delete_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        res = pkg.resources[0]
        assert len(pkg.resources) == 2, pkg.resources
        rev = model.repo.new_revision()
        res.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 1, pkg.resources
        assert len(pkg.package_resources_all) == 2, pkg.package_resources_all
    
    def test_03_reorder_resources(self):
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        res0 = pkg.resources[0]
        del pkg.resources[0]
        pkg.resources.append(res0)
        # this assert will fail
        # assert pkg.resources[1].position == 1
        # Why? According to docs for ordering list it does not reorder appended
        # elements by default (see
        # http://www.sqlalchemy.org/trac/browser/lib/sqlalchemy/ext/orderinglist.py#L197)
        # so we have to call reorder directly in supported versions
        # of sqlalchemy and set position to None in older ones.
        if sqav.startswith("0.4"):
            pkg.resources[1].position = None
        else:
            pkg.resources.target.reorder()            
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 2, pkg.package_resources_all
        lastres = pkg.resources[1]
        assert lastres.position == 1, lastres
        assert lastres.url == self.urls[0]
        

    def test_04_insert_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        rev = model.repo.new_revision()
        newurl = u'http://xxxxxxxxxxxxxxx'

        resource = model.PackageResource(url=newurl)

        pkg.resources.insert(0, resource)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 3, pkg.resources
        assert pkg.resources[1].url == self.urls[0]
        assert len(pkg.resources[1].all_revisions) == 2

    def test_05_delete_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.PackageResource)
        active_resources = model.Session.query(model.PackageResource).\
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

    def test_06_purge_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.PackageResource).all()
        assert len(all_resources) == 2, pkg.resources
        rev = model.repo.new_revision()
        pkg.purge()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.PackageResource).\
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
        for url in self.urls:
            pkg.resources.append(model.PackageResource(url=url,
                                       format=self.format,
                                       description=self.description,
                                       hash=self.hash))
        model.repo.commit_and_remove()        

    @classmethod
    def teardown(self):
        model.Session.remove()
        model.repo.clean_db()


    def test_1_update_resources_no_ids(self):
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
                'description':self.description, 'hash':self.hash},
            { #slightly different
                'url':self.urls[1], 'format':u'OTHER FORMAT',
                'description':self.description, 'hash':self.hash},
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
        assert pkg.resources[1].id != original_res_ids[1]

        # package resource revisions
        prr_q = model.Session.query(model.PackageResourceRevision)
        assert len(prr_q.all()) == offset + 2 + 1, prr_q.all() # 2 deletions, 1 new one
        prr1 = prr_q.\
               filter_by(revision_id=rev.id).\
               order_by(model.resource_revision_table.c.position).\
               filter_by(state=model.State.ACTIVE).one()
        assert prr1.package == pkg, prr1.package
        assert prr1.url == self.urls[1], '%s != %s' % (prr1.url, self.urls[1])
        assert prr1.revision.id == rev.id, '%s != %s' % (prr1.revision.id, rev.id)
        # revision contains package resource revisions
        rev_prrs = model.repo.list_changes(rev)[model.PackageResource]
        assert len(rev_prrs) == 3, rev_prrs # 2 deleted, 1 new

        # previous revision still contains previous ones
        previous_rev = model.repo.history()[1]
        previous_rev_prrs = model.repo.list_changes(previous_rev)[model.PackageResource]
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

1
