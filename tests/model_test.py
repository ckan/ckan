import py.test

import ckan.model
# mod = ckan.model.DomainModel()
# mod.rebuild()

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
    package = ckan.model.Package(title='The Ninth Symphony')

    def setup_class(self):
        newrev = self.mod.begin_revision()
        self.title = 'La boheme'
        self.newnotes = 'Written by Puccini'
        self.packagerev = self.mod.packages.create(newrev, title=self.title, notes='blah')
        self.packagerev.notes = self.newnotes 
        newrev.commit(message='Creating a package')

    def test_create_package(self):
        # test the revision
        out = ckan.model.PackageRevision.get(self.packagerev.id)
        assert out.title == self.title
        assert out.notes == self.newnotes
        # test the base object
        out = ckan.model.Package.get(self.packagerev.base.id)
        assert out.title == self.title
        assert out.notes == self.newnotes

    def test_change_package(self):
        newrev = self.mod.begin_revision()
        # package = newrev.package_revisions.by_name('beethoven_ninth') 
        # package.notes = 'Written by Beethoven'
        # newrev.commit(msg='Creating a package')

