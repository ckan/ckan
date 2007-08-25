import py.test

# needed for config to be set and db access to work
import ckan.tests
import ckan.exceptions
import ckan.models

from datetime import datetime


class TestLicense:
    name = 'testlicense'

    def teardown_class(cls):
        license = ckan.models.License.byName(cls.name)
        ckan.models.License.delete(license.id)

    def test_license(self):
        license = ckan.models.License(name=self.name)
        exp = ckan.models.License.byName(self.name)
        assert exp.id == license.id


class TestPackage:

    def setup_class(self):
        self.repo = ckan.models.repo
        self.name = 'geodata'
        self.notes = 'Written by Puccini'
        txn = self.repo.begin_transaction()
        self.pkg1 = txn.model.packages.create(name=self.name)
        self.pkg1.notes = self.notes
        txn.commit()

    def teardown_class(self):
        self.pkg1.purge()

    def test_create_package(self):
        rev = self.repo.youngest_revision()
        out = rev.model.packages.get(self.name)
        assert out.name == self.name
        assert out.notes == self.notes

    def test_update_package(self):
        newnotes = 'Written by Beethoven'
        author = 'jones'
        txn = self.repo.begin_transaction()
        pkg = txn.model.packages.get(self.name)
        pkg.notes = newnotes
        txn.author = 'jones'
        txn.commit()
        newrev = self.repo.youngest_revision()
        outpkg = newrev.model.packages.get(self.name)
        assert outpkg.notes == newnotes
        assert len(outpkg.history) > 0
        assert outpkg.history[-1].revision.author == author


class TestPackageWithTags:
    """
    WARNING: with sqlite these tests may fail (depending on the order they are
    run in) as sqlite does not support ForeignKeys properly.
    """

    def setup_class(self):
        self.repo = ckan.models.repo

        txn = self.repo.begin_transaction()
        self.tagname = 'testtagm2m'
        self.tagname2 = 'testtagm2m2'
        self.tagname3 = 'testtag3'
        self.pkgname = 'testpkgm2m'
        pkg = txn.model.packages.create(name=self.pkgname)
        self.tag = txn.model.tags.create(name=self.tagname)
        self.tag2 = txn.model.tags.create(name=self.tagname2)
        pkg2tag = txn.model.package_tags.create(package=pkg, tag=self.tag)
        self.pkg2tag_id = pkg2tag.id
        pkg.tags.create(tag=self.tag2)
        txn.commit()
        self.rev = self.repo.youngest_revision()

    def teardown_class(self):
        rev = self.repo.youngest_revision()
        rev.model.packages.purge(self.pkgname)
        rev.model.tags.purge(self.tagname)
        rev.model.tags.purge(self.tagname2)
        rev.model.tags.purge(self.tagname3)

    def test_1(self):
        pkg = self.rev.model.packages.get(self.pkgname)
        pkg2tag = self.rev.model.package_tags.get(self.pkg2tag_id)
        assert pkg2tag.package.name == self.pkgname

    def test_2(self):
        pkg = self.rev.model.packages.get(self.pkgname)
        pkg2tag = pkg.tags.get(self.tag2)
        assert pkg2tag.package.name == self.pkgname
        pkg2tag2 = pkg.tags.get(self.tag)
        assert pkg2tag2.package.name == self.pkgname
        assert pkg2tag2.tag.name == self.tagname

    def test_list(self):
        pkg = self.rev.model.packages.get(self.pkgname)

        # 2 default packages each with 2 tags so we have 2 + 4
        all = self.rev.model.package_tags.list() 
        assert len(all) == 6
        pkgtags = pkg.tags.list()
        assert len(pkgtags) == 2

    def test_add_tag_by_name(self):
        txn = self.repo.begin_transaction()
        pkg = txn.model.packages.get(self.pkgname)
        pkg.add_tag_by_name(self.tagname3)
        txn.commit()
        newrev = self.repo.youngest_revision()
        outpkg = newrev.model.packages.get(self.pkgname)
        assert len(outpkg.tags.list()) == 3
        # assert len(self.tag1.packages) == 1

#    def test_add_tag_by_name_existing(self):
#        pkg = self.pkg1
#        pkg.add_tag_by_name(self.tag1.name)
#        pkg.save()
#        outpkg = self.dm.packages.get(self.pkg1.name)
#        assert len(outpkg.tags) == 1
    

class TestPackageWithLicense:

    def setup_class(self):
        self.repo = ckan.models.repo
        self.license1 = ckan.models.License(name='test_license1')
        self.license2 = ckan.models.License(name='test_license2')
        txn = self.repo.begin_transaction()
        self.pkgname = 'testpkgfk'
        pkg = txn.model.packages.create(name=self.pkgname)
        pkg.license = self.license1
        txn.commit()

        txn2 = self.repo.begin_transaction()
        pkg = txn2.model.packages.get(self.pkgname)
        pkg.license = self.license2
        txn2.commit()
        self.rev1id = txn.id
        self.rev2id = txn2.id

    def teardown_class(self):
        rev = self.repo.youngest_revision()
        rev.model.packages.purge(self.pkgname)
        ckan.models.License.delete(self.license1.id)
        ckan.models.License.delete(self.license2.id)
 
    def test_set1(self):
        rev = self.repo.get_revision(self.rev1id)
        pkg = rev.model.packages.get(self.pkgname)
        out = pkg.license.name 
        exp = self.license1.name
        assert out == exp

    def test_set2(self):
        rev = self.repo.get_revision(self.rev2id)
        pkg = rev.model.packages.get(self.pkgname)
        out = pkg.license.name 
        exp = self.license2.name
        assert out == exp

class TestTag:

    def test_search_1(self):
        out = list(ckan.models.Tag.search_by_name('russian'))
        assert len(out) == 1
        assert out[0].name == 'russian'

    def test_search_2(self):
        out = list(ckan.models.Tag.search_by_name('us'))
        assert len(out) == 1

    def test_search_3(self):
        out = list(ckan.models.Tag.search_by_name('s'))
        assert len(out) == 2
