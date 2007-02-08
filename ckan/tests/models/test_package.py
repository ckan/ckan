import py.test

# needed for config to be set and db access to work
import ckan.tests
import ckan.exceptions
import ckan.models

from datetime import datetime

class TestRevision:
    dm = ckan.models.dm
    rr = ckan.models.Revision()

    def teardown_class(cls):
        ckan.models.Revision.delete(cls.rr.id)

    def test_revision(self):
        self.rr.log = 'This is a log'
        self.rr.author = 'tolstoy'
        self.rr.date = datetime.now()
        rr2 = ckan.models.Revision.get(self.rr.id)
        assert rr2.log == self.rr.log

class TestTag:
    dm = ckan.models.dm
    name = 'testtag'

    def teardown_class(cls):
        tag = ckan.models.Tag.byName(cls.name)
        ckan.models.Tag.delete(tag.id)

    def test_tag(self):
        tag = ckan.models.Tag(name=self.name)
        created = str(tag.created)
        exp = str(datetime.now())
        assert created[:10] == exp[:10]


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

class TestPackageWithTags:
    """
    WARNING: with sqlite these tests may fail (depending on the order they are
    run in) as sqlite does not support RelatedJoin properly.
    """

    dm  = ckan.models.dm

    def setup_method(self, method): 
        self.name = 'geodata'
        self.tagname1 = 'testtag1'
        self.tagname2 = 'geodata'
        try:
            self.teardown_method()
        except:
            pass
        self.pkg1 = self.dm.packages.create(name=self.name)
        self.tag1 = ckan.models.Tag(name=self.tagname1)

    def teardown_method(self, method):
        self.dm.packages.purge(self.name)
        tag = ckan.models.Tag.byName(self.tagname1)
        ckan.models.Tag.delete(tag.id)
        if method == 'test_add_tag_by_name':
            tag = ckan.models.Tag.byName(self.tagname2)
            ckan.models.Tag.delete(tag.id)

    def test_addTag(self):
        pkg = self.dm.packages.get(self.pkg1.name)
        print pkg.id
        pkg.addTag(self.tag1)
        author = 'jones'
        pkg.save(author=author, log='a log message')
        outpkg = self.dm.packages.get(self.pkg1.name)
        print outpkg.tags
        assert len(outpkg.tags) == 1
        assert len(outpkg.revisions) > 1
        assert outpkg.revisions[-1].author == author

    def test_add_tag_by_name(self):
        pkg = self.dm.packages.get(self.pkg1.name)
        pkg.addTag(self.tag1)
        pkg.add_tag_by_name(self.tagname2)
        pkg.save()
        outpkg = self.dm.packages.get(self.pkg1.name)
        assert len(outpkg.tags) == 2

