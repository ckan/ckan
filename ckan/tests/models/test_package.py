import py.test

# needed for config to be set and db access to work
import ckan.tests
import ckan.exceptions
import ckan.models

from datetime import datetime

class TestRevision:
    dm = ckan.models.dm

    def test_revision(self):
        rr = ckan.models.Revision()
        rr.log = 'This is a log'
        rr.author = 'tolstoy'
        rr.date = datetime.now()
        rr2 = ckan.models.Revision.get(rr.id)
        assert rr2.log == rr.log


class TestPackage:

    dm = ckan.models.dm

    def setup_class(self):
        # create a package the 'crude' way (without a revision)
        self.name = 'geodata'
        self.notes = 'Written by Puccini'
        self.name2 = 'geodata2'
        self.pkg1 = ckan.models.Package(name=self.name, notes=self.notes)

    def teardown_class(self):
        self.dm.packages.purge(self.pkg1.name)
        self.dm.packages.purge(self.name2)

    def test_create_package(self):
        out = self.dm.packages.get(self.name)
        assert out.name == self.name
        assert out.notes == self.notes

    def test_package_purge(self):
        name = 'somename'
        pkg = self.dm.packages.create(name=name)
        self.dm.packages.purge(name)
        results = list(ckan.models.Package.select(
            ckan.models.Package.q.name==name))
        assert len(results) == 0 

    def test_create_package_2(self):
        # now do it the proper way
        author = 'jones2'
        self.pkg2 = self.dm.packages.create(author,
                name=self.name2,
                notes=self.notes)
        out = self.dm.packages.get(self.name2)
        assert out.notes == self.notes
        assert out.revisions[0].author == author

    def test_update_package(self):
        newnotes = 'Written by Beethoven'
        pkg = self.dm.packages.get(self.pkg1.name)
        pkg.notes = newnotes
        author = 'jones'
        pkg.save(author=author, log='a log message')
        outpkg = self.dm.packages.get(self.pkg1.name)
        assert outpkg.notes == newnotes
        assert len(outpkg.revisions) > 0
        assert outpkg.revisions[-1].author == author
        # have a teardown method to reset values?
        # as py.test guarantees order of execution might not be necessary

