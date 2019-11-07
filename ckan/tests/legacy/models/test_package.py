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
