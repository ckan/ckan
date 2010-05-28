from ckan.tests import *
import ckan.model as model

class TestPackageResource:
    def setup(self):
        self.pkgname = u'resourcetest'
        assert not model.Package.by_name(self.pkgname)
        assert model.Session.query(model.PackageResource).count() == 0
        self.urls = [u'http://somewhere.com/', u'http://elsewhere.com/']
        self.format = u'csv'
        self.description = u'Important part.'
        self.hash = u'abc123'
        rev = model.repo.new_revision()
        pkg = model.Package(name=self.pkgname)
        model.Session.add(pkg)
        for url in self.urls:
            pr = model.PackageResource(url=url,
                                       format=self.format,
                                       description=self.description,
                                       hash=self.hash,
                                       )
            pkg.resources.append(pr)
        model.repo.commit_and_remove()

    def teardown(self):
        model.Session.remove()
        pkg = model.Package.by_name(self.pkgname)
        if pkg:
            pkg.purge()
        model.repo.commit_and_remove()

    def test_01_create_package_resources(self):
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == len(self.urls), pkg.resources
        assert pkg.resources[0].url == self.urls[0], pkg.resources[0]
        assert pkg.resources[0].description == self.description, pkg.resources[0]
        assert pkg.resources[0].hash == self.hash, pkg.resources[0]
        assert pkg.resources[0].position == 0, pkg.resources[0].position
        resources = pkg.resources
        assert resources[0].package == pkg, resources[0].package

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
        pkg = model.Package.by_name(self.pkgname)
        rev = model.repo.new_revision()
        res0 = pkg.resources[0]
        del pkg.resources[0]
        pkg.resources.append(res0)
        # this assert will fail
        # assert pkg.resources[1].position == 1
        # Why? According to docs for ordering list it does not reorder appended
        # elements by default (see
        # http://www.sqlalchemy.org/trac/browser/lib/sqlalchemy/ext/orderinglist.py#L197)
        # Possible ways to deal with this:
        # 1. Call reorder() on list. Problematic as this method is hidden by
        #   StatefulList()
        # 2. set res0.position = None
        pkg.resources[1].position = None
        print [ p.url for p in pkg.resources ]
        print [ p.position for p in pkg.resources ]
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 2, pkg.package_resources_all
        print [ p.url for p in pkg.resources ]
        print [ p.position for p in pkg.resources ]
        lastres = pkg.resources[1]
        assert lastres.position == 1, lastres
        assert lastres.url == self.urls[0], pkg.lastres

    def test_04_insert_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        rev = model.repo.new_revision()
        newurl = u'http://xxxxxxxxxxxxxxx'
        pkg.resources.insert(0, model.PackageResource(url=newurl))
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
        model.repo.rebuild_db()


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

