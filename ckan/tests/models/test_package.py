import py.test

# needed for config to be set and db access to work
import ckan.tests
import ckan.exceptions
import ckan.models

class TestRevision:
    dm = ckan.models.dm

    def test_revision(self):
        rr = ckan.models.Revision()
        rr.message = 'This is a message'
        rr2 = ckan.models.Revision.get(rr.id)
        assert rr2.message == rr.message

    def test_revision_2(self):
        newrev = self.dm.begin_revision()
        py.test.raises(ckan.exceptions.EmptyRevisionException, newrev.commit,
                'This is an empty revision')


class TestPackage:

    dm = ckan.models.dm
    pkgreg = ckan.models.dm.packages

    def setup_class(self):
        # create a package the 'crude' way (without a revision)
        self.pkg1 = ckan.models.Package(name='geodata')
        newrev = self.dm.begin_revision()
        self.name = 'geodata2'
        self.newnotes = 'Written by Puccini'
        self.packagerev = self.dm.packages.create(newrev, name=self.name, notes='blah')
        self.packagerev.notes = self.newnotes 
        newrev.commit(message='Creating a package')

    def teardown_class(self):
        ckan.models.Package.purge(self.pkg1.id)
        ckan.models.Package.purge(self.packagerev.base.id)

    def test_registry_get(self):
        pkg = self.pkgreg.get(self.name)
        assert pkg.notes == self.newnotes
        # TODO
        # ensure you cannot write on pkg
        # py.test.raises(...)

    def test_create_package(self):
        # test the revision
        out = ckan.models.PackageRevision.get(self.packagerev.id)
        assert out.name == self.name
        assert out.notes == self.newnotes
        # test the base object
        out = ckan.models.Package.get(self.packagerev.base.id)
        assert out.name == self.name
        assert out.notes == self.newnotes

    def test_package_purge(self):
        newrev = self.dm.begin_revision()
        pkgrev = self.dm.packages.create(newrev, name='somename')
        newrev.commit(message='testing purge')
        id = pkgrev.base.id
        ckan.models.Package.purge(id)
        results = list(ckan.models.Package.select(ckan.models.Package.q.id==id))
        assert len(results) == 0 

    def test_change_package(self):
        newrev = self.dm.begin_revision()
        newnotes = 'Written by Beethoven'
        packagerev = self.dm.packages.get(self.pkg1.name, newrev)
        packagerev.notes = newnotes
        newrev.commit(message='Modifying a package')
        outpkg = self.pkgreg.get(self.pkg1.name)
        assert outpkg.notes == newnotes
        assert len(outpkg.revisions) > 0
        # have a teardown method to reset values?
        # as py.test guarantees order of execution might not be necessary

    def test_commit_locking(self):
        # TODO: if edit simultaneously get a conflict warning ...
        pass

    def test_delete_package(self):
        pass

