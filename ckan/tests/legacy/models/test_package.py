# encoding: utf-8

from nose.tools import assert_equal

from ckan.tests.legacy import *
import ckan.model as model

# Todo: More domain logic tests e.g. for isopen() and other domain logic.

class TestPackage:
    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.name = u'geodata'
        self.notes = 'A <b>great</b> package <script href="dodgy.js"/> like package:pollution_stats'
        pkgs = model.Session.query(model.Package).filter_by(name=self.name).all()
        for p in pkgs:
            p.purge()
        model.Session.commit()
        self.pkg1 = model.Package(name=self.name)
        model.Session.add(self.pkg1)
        self.pkg1.notes = self.notes
        self.pkg1.license_id = u'odc-by'
        model.Session.commit()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        pkg1 = model.Session.query(model.Package).filter_by(name=self.name).one()

        pkg1.purge()
        model.Session.commit()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_create_package(self):
        package = model.Package.by_name(self.name)
        assert package.name == self.name
        assert package.notes == self.notes
        assert package.license.id == u'odc-by'
        assert package.license.title == u'Open Data Commons Attribution License', package.license.title

    def test_update_package(self):
        newnotes = u'Written by Beethoven'
        author = u'jones'

        pkg = model.Package.by_name(self.name)
        pkg.notes = newnotes
        model.Session.commit()
        try:
            model.Session.expunge_all()
        except AttributeError: # sqlalchemy 0.4
            model.Session.clear()
        outpkg = model.Package.by_name(self.name)
        assert outpkg.notes == newnotes

    def test_package_license(self):
        # Check unregistered license_id causes license to be 'None'.
        package = model.Package.by_name(self.name)
        package.license_id = u'zzzzzzz'
        assert package.license == None
        model.Session.remove() # forget change

    def test_as_dict(self):
        pkg = model.Package.by_name(self.name)
        out = pkg.as_dict()
        assert out['name'] == pkg.name
        assert out['license'] == pkg.license.title
        assert out['license_id'] == pkg.license.id
        assert out['tags'] == [tag.name for tag in pkg.get_tags()]
        assert out['metadata_modified'] == pkg.metadata_modified.isoformat()
        assert out['metadata_created'] == pkg.metadata_created.isoformat()
        assert_equal(out['notes'], pkg.notes)
        assert_equal(out['notes_rendered'], '<p>A great package  like <a href="/dataset/pollution_stats">package:pollution_stats</a></p>')


class TestPackageWithTags:
    """
    WARNING: with sqlite these tests may fail (depending on the order they are
    run in) as sqlite does not support ForeignKeys properly.
    """
    # Todo: Remove comment, since it pertains to sqlite, which CKAN doesn't support?

    @classmethod
    def setup_class(self):
        model.repo.init_db()
        self.tagname = u'test tag m2m!'
        self.tagname2 = u'testtagm2m2'
        self.tagname3 = u'test tag3!'
        self.pkgname = u'testpkgm2m'
        pkg = model.Package(name=self.pkgname)
        self.tag = model.Tag(name=self.tagname)
        self.tag2 = model.Tag(name=self.tagname2)
        pkg2tag = model.PackageTag(package=pkg, tag=self.tag)
        pkg.add_tag(self.tag2)
        model.Session.add_all([pkg,self.tag,self.tag2,pkg2tag])
        model.Session.commit()
        self.pkg2tag_id = pkg2tag.id

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1(self):
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.get_tags()) == 2
        # pkg2tag = model.Session.query(model.PackageTag).get(self.pkg2tag_id)
        # assert pkg2tag.package.name == self.pkgname

    def test_tags(self):
        pkg = model.Package.by_name(self.pkgname)
        # TODO: go back to this
        # 2 default packages each with 2 tags so we have 2 + 4
        all = model.Session.query(model.Tag).all()
        assert len(all) == 3, all

    def test_add_tag_by_name(self):
        pkg = model.Package.by_name(self.pkgname)
        pkg.add_tag_by_name(self.tagname3)
        model.Session.commit()
        try:
            model.Session.expunge_all()
        except AttributeError: # sqlalchemy 0.4
            model.Session.clear()
        outpkg = model.Package.by_name(self.pkgname)
        assert len(outpkg.get_tags()) == 3
        t1 = model.Tag.by_name(self.tagname)
        assert len(t1.package_tags) == 1

    def test_add_tag_by_name_existing(self):
        try:
            model.Session.expunge_all()
        except AttributeError: # sqlalchemy 0.4
            model.Session.clear()
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.get_tags()) == 3, len(pkg.get_tags())
        pkg.add_tag_by_name(self.tagname)
        assert len(pkg.get_tags()) == 3


class TestPackageTagSearch:
    @classmethod
    def setup_class(self):
        CreateTestData.create()

        self.orderedfirst = u'000-zzz'
        # tag whose association will get deleted
        self.tagname = u'russian-tag-we-will-delete'
        tag3 = model.Tag(name=self.tagname)
        pkg = model.Package.by_name(u'annakarenina')
        pkg.add_tag(tag3)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'annakarenina')
        pkg.remove_tag(tag3)
        # now do a tag for ordering
        tagordered = model.Tag(name=self.orderedfirst)
        wap = model.Package.by_name(u'warandpeace')
        # do them the wrong way round
        wap.add_tag(tagordered)
        pkg.add_tag(tagordered)
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_0_deleted_package_tags(self):
        pkg = model.Package.by_name(u'annakarenina')
        tag = model.Tag.by_name(self.tagname)
        assert len(pkg.get_tags()) == 4, len(pkg.get_tags())
        assert len(tag.packages) == 0

    def test_1_tag_search_1(self):
        out = list(model.Tag.search_by_name(u'russian'))
        assert len(out) == 2
        assert out[0].name == 'russian'

    def test_1_tag_search_2(self):
        out = list(model.Tag.search_by_name(u'us'))
        assert len(out) == 2

    def test_1_tag_search_3(self):
        out = list(model.Tag.search_by_name(u's'))
        assert len(out) == 3

    def test_alphabetical_ordering(self):
        pkg = model.Package.by_name(u'annakarenina')
        tag = pkg.get_tags()[0]
        assert tag.name == self.orderedfirst
        assert tag.packages[0].name == 'annakarenina', tag.packages


class TestPackagePurge:
    @classmethod
    def setup_class(self):
        CreateTestData.create()
    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
    def test_purge(self):
        pkgs = model.Session.query(model.Package).all()
        for p in pkgs:
           p.purge()
        model.Session.commit()
        pkgs = model.Session.query(model.Package).all()
        assert len(pkgs) == 0


