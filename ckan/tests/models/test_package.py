import py.test

# needed for config to be set and db access to work
import ckan.tests
import ckan.exceptions
import ckan.models
mod = ckan.models.DomainModel
mod.rebuild()

class TestRevision:
    mod = ckan.models.DomainModel()

    def test_revision(self):
        rr = ckan.models.Revision()
        rr.message = 'This is a message'
        rr2 = ckan.models.Revision.get(rr.id)
        assert rr2.message == rr.message

    def test_revision_2(self):
        newrev = self.mod.begin_revision()
        py.test.raises(ckan.exceptions.EmptyRevisionException, newrev.commit,
                'This is an empty revision')


class TestModel:

    mod = ckan.models.DomainModel()

    def setup_class(self):
        # create a package the 'crude' way (without a revision)
        self.package = ckan.models.Package(name='geodata')
        newrev = self.mod.begin_revision()
        self.name = 'geodata2'
        self.newnotes = 'Written by Puccini'
        self.packagerev = self.mod.packages.create(newrev, name=self.name, notes='blah')
        self.packagerev.notes = self.newnotes 
        newrev.commit(message='Creating a package')

    def teardown_class(self):
        ckan.models.Package.purge(self.package.id)
        ckan.models.Package.purge(self.packagerev.base.id)

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
        newrev = self.mod.begin_revision()
        pkgrev = self.mod.packages.create(newrev, name='somename')
        newrev.commit(message='testing purge')
        id = pkgrev.base.id
        ckan.models.Package.purge(id)
        results = list(ckan.models.Package.select(ckan.models.Package.q.id==id))
        assert len(results) == 0 

    def test_commit_locking(self):
        # TODO: if edit simultaneously get a conflict warning ...
        pass

#    def test_change_package(self):
#        newrev = self.mod.begin_revision()
#        # really i am getting package revision ...
#        # what happens if I do a get on this though?
#        packagerev = mod.packages.get(self.package.id, newrev)
#        packagerev.notes = 'Written by Beethoven'
#        newrev.commit(msg='Modifying a package')


    def test_delete_package(self):
        pass

