from ckan.tests import *
import ckan.model as model

class TestResourceLifecycle:
    @classmethod
    def setup_class(self):
        self.pkgname = u'geodata'
        self.urls = [u'http://somewhere.com/', u'http://elsewhere.com/']
        self.format = u'csv'
        self.description = u'Important part.'
        self.hash = u'abc123'
        rev = model.repo.new_revision()
        self.pkg = model.Package(name=self.pkgname)
        model.Session.save(self.pkg)
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_0_create_package_resources(self):
        pkg = model.Package.by_name(self.pkgname)
        rev = model.repo.new_revision()
        for url in self.urls:
            pr = model.PackageResource(url=url,
                                       format=self.format,
                                       description=self.description,
                                       hash=self.hash,
                                       )
            model.Session.save(pr)
            pkg.resources.append(pr)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == len(self.urls), pkg.resources
        assert pkg.resources[0].url == self.urls[0], pkg.resources[0]
        assert pkg.resources[0].description == self.description, pkg.resources[0]
        assert pkg.resources[0].hash == self.hash, pkg.resources[0]
        assert pkg.resources[0].position == 0, pkg.resources[0].position
        resources = pkg.resources
        assert resources[0].package == pkg, resources[0].package

    def _test_1_delete_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        res = pkg.resources[0]
        assert len(pkg.resources) == 2, pkg.resources
        rev = model.repo.new_revision()
        res.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 1, pkg.resources

    def test_2_delete_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.PackageResource).all()
        assert len(all_resources) == 2, pkg.resources
        rev = model.repo.new_revision()
        pkg.purge()
        model.repo.commit_and_remove()

        active_id = model.Session.query(model.State).filter_by(name='active').one().id
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.PackageResource).\
                        filter_by(state_id=active_id).all()
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
            model.Session.save(pr)
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
        model.Session.save(pr)
        self.pkg.resources.insert(1, pr)
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(self.pkgname)
        resources = self.pkg.resources
        assert resources[0].url == self.urls[0], resources[index]
        assert resources[1].url == u'new.url', resources[index]
        assert resources[3].url == self.urls[2], resources[index]
