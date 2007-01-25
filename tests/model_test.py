import py.test

import ckan.model
mod = ckan.model.DomainModel()
mod.rebuild()

class TestRevision:
    mod = ckan.model.DomainModel()

    def test_revision(self):
        rr = ckan.model.Revision()
        rr.message = 'This is a message'
        rr2 = ckan.model.Revision.get(rr.id)
        assert rr2.message == rr.message

    def test_revision_2(self):
        newrev = self.mod.begin_revision()
        py.test.raises(ckan.model.EmptyRevisionException, newrev.commit, 'This is an empty revision')


class TestModel:

    mod = ckan.model.DomainModel()

    def setup_class(self):
        # create a package the 'crude' way (without a revision)
        self.package = ckan.model.Package(title='The Ninth Symphony')
        newrev = self.mod.begin_revision()
        self.title = 'La boheme'
        self.newnotes = 'Written by Puccini'
        self.packagerev = self.mod.packages.create(newrev, title=self.title, notes='blah')
        self.packagerev.notes = self.newnotes 
        newrev.commit(message='Creating a package')

    def teardown_class(self):
        ckan.model.Package.purge(self.package.id)
        ckan.model.Package.purge(self.packagerev.base.id)

    def test_create_package(self):
        # test the revision
        out = ckan.model.PackageRevision.get(self.packagerev.id)
        assert out.title == self.title
        assert out.notes == self.newnotes
        # test the base object
        out = ckan.model.Package.get(self.packagerev.base.id)
        assert out.title == self.title
        assert out.notes == self.newnotes

    def test_package_purge(self):
        newrev = self.mod.begin_revision()
        pkgrev = self.mod.packages.create(newrev, title='sometitle')
        newrev.commit(message='testing purge')
        id = pkgrev.base.id
        ckan.model.Package.purge(id)
        results = list(ckan.model.Package.select(ckan.model.Package.q.id==id))
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

