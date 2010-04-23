from ckan.tests import *
import ckan.model as model

class TestResourceLifecycle:
    @classmethod
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

    @classmethod
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
        print [ p.url for p in pkg.resources ]
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 2, pkg.package_resources_all
        print [ p.url for p in pkg.resources ]
        print [ p.position for p in pkg.resources ]
        assert pkg.resources[1].url == self.urls[0], pkg.resources[1]

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
        all_resources = model.Session.query(model.PackageResource).all()
        assert len(all_resources) == 2, pkg.resources
        rev = model.repo.new_revision()
        pkg.purge()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.PackageResource).\
                        filter_by(state=model.State.ACTIVE).all()
        assert len(all_resources) == 0, pkg.resources


class TestResourceUse:
    @classmethod
    def setup_class(self):
        self.pkgname = u'geodata'
        self.urls = ['http://urlC.1/', 'http://urlB.2/', 'http://urlA.3/']
        self.formats = [u'csv', u'json', u'xml']
        self.description = u'Important part.'
        self.hash = u'abc123'
        rev = model.repo.new_revision()
        pkg = model.Package(name=self.pkgname)
        for index, url in enumerate(self.urls):
            pr = model.PackageResource(url=unicode(url),
                                       format=self.formats[index],
                                       description=self.description,
                                       hash=self.hash,
                                       )
            model.Session.add(pr)
            pkg.resources.append(pr)
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(self.pkgname)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_0_order_correct_at_start(self):
        resources = self.pkg.resources
        for index, urls in enumerate(self.urls):
            assert resources[index].url == self.urls[index], resources[index]
            assert resources[index].position == index, '%i %i' % (resources[index].position, index)

    def test_1_reorder(self):
        resources = self.pkg.resources
        rev = model.repo.new_revision()
        pr = model.PackageResource(url=u'new.url')
        model.Session.add(pr)
        self.pkg.resources.insert(1, pr)
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(self.pkgname)
        resources = self.pkg.resources
        assert resources[0].url == self.urls[0], resources[index]
        assert resources[1].url == u'new.url', resources[index]
        assert resources[3].url == self.urls[2], resources[index]
