# encoding: utf-8

import pytest
from ckan.tests.legacy import CreateTestData
import ckan.model as model

# Todo: More domain logic tests e.g. for isopen() and other domain logic.


class TestPackage:
    name = u"geodata"

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        notes = 'A <b>great</b> package <script href="dodgy.js"/> like package:pollution_stats'
        pkgs = (
            model.Session.query(model.Package).filter_by(name=self.name).all()
        )
        for p in pkgs:
            p.purge()
        model.Session.commit()
        rev = model.repo.new_revision()
        pkg1 = model.Package(name=self.name)
        model.Session.add(pkg1)
        pkg1.notes = notes
        pkg1.license_id = u"odc-by"
        model.Session.commit()
        model.Session.remove()

    def test_basic_revisioning(self):
        # create a package with package_fixture_data
        name = "frob"
        rev = model.repo.new_revision()
        package = model.Package(name=name)
        model.Session.add(package)
        model.Session.flush()
        revision_id = model.Session().revision.id
        timestamp = model.Session().revision.timestamp
        model.repo.commit_and_remove()

        package = model.Package.by_name(name)
        assert len(package.all_revisions) == 1
        assert package.all_revisions[0].revision_id == revision_id
        assert package.all_revisions[0].revision_timestamp == timestamp

        # change it
        rev = model.repo.new_revision()
        package = model.Package.by_name(name)
        package.title = "wobsnasm"
        revision_id2 = model.Session().revision.id
        timestamp2 = model.Session().revision.timestamp
        model.repo.commit_and_remove()

        package = model.Package.by_name(name)
        assert len(package.all_revisions) == 2
        assert package.all_revisions[0].revision_id == revision_id2
        assert package.all_revisions[0].revision_timestamp == timestamp2

        assert package.all_revisions[1].revision_id == revision_id
        assert package.all_revisions[1].revision_timestamp == timestamp

    def test_as_dict(self):
        pkg = model.Package.by_name(self.name)
        out = pkg.as_dict()
        assert out["name"] == pkg.name
        assert out["license"] == pkg.license.title
        assert out["license_id"] == pkg.license.id
        assert out["tags"] == [tag.name for tag in pkg.get_tags()]
        assert out["metadata_modified"] == pkg.metadata_modified.isoformat()
        assert out["metadata_created"] == pkg.metadata_created.isoformat()
        assert out["notes"] == pkg.notes
        assert (
            out["notes_rendered"]
            == '<p>A great package  like <a href="/dataset/pollution_stats">package:pollution_stats</a></p>'
        )


class TestPackageTagSearch:
    orderedfirst = u"000-zzz"
    tagname = u"russian-tag-we-will-delete"

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        model.repo.new_revision()

        # tag whose association will get deleted
        tag3 = model.Tag(name=self.tagname)
        pkg = model.Package.by_name(u"annakarenina")
        pkg.add_tag(tag3)
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Package.by_name(u"annakarenina")
        pkg.remove_tag(tag3)
        # now do a tag for ordering
        tagordered = model.Tag(name=self.orderedfirst)
        wap = model.Package.by_name(u"warandpeace")
        # do them the wrong way round
        wap.add_tag(tagordered)
        pkg.add_tag(tagordered)
        model.repo.commit_and_remove()

    def test_0_deleted_package_tags(self):
        pkg = model.Package.by_name(u"annakarenina")
        tag = model.Tag.by_name(self.tagname)
        assert len(pkg.get_tags()) == 4, len(pkg.get_tags())
        assert len(tag.packages) == 0

    def test_1_tag_search_1(self):
        out = list(model.Tag.search_by_name(u"russian"))
        assert len(out) == 2
        assert out[0].name == "russian"

    def test_1_tag_search_2(self):
        out = list(model.Tag.search_by_name(u"us"))
        assert len(out) == 2

    def test_1_tag_search_3(self):
        out = list(model.Tag.search_by_name(u"s"))
        assert len(out) == 3

    def test_alphabetical_ordering(self):
        pkg = model.Package.by_name(u"annakarenina")
        tag = pkg.get_tags()[0]
        assert tag.name == self.orderedfirst
        assert tag.packages[0].name == "annakarenina", tag.packages


class TestPackageRevisions:
    name = u"revisiontest"

    @pytest.fixture
    def initial_data(self, clean_db):

        # create pkg
        notes = [
            u"Written by Puccini",
            u"Written by Rossini",
            u"Not written at all",
            u"Written again",
            u"Written off",
        ]
        rev = model.repo.new_revision()
        pkg1 = model.Package(name=self.name)
        model.Session.add(pkg1)
        pkg1.notes = notes[0]
        pkg1.extras["mykey"] = notes[0]
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            pkg1 = model.Package.by_name(self.name)
            pkg1.notes = notes[i]
            pkg1.extras["mykey"] = notes[i]
            model.repo.commit_and_remove()

        pkg1 = model.Package.by_name(self.name)
        return pkg1, notes

    def test_1_all_revisions(self, initial_data):
        pkg1, notes = initial_data
        all_rev = pkg1.all_revisions
        num_notes = len(notes)
        assert len(all_rev) == num_notes, len(all_rev)
        for i, rev in enumerate(all_rev):
            assert rev.notes == notes[num_notes - i - 1], "%s != %s" % (
                rev.notes,
                notes[i],
            )


class TestRelatedRevisions:
    @pytest.mark.usefixtures("clean_db")
    def test_1_all_revisions(self):
        CreateTestData.create()
        model.Session.remove()
        self.name = u"difftest"

        # create pkg - PackageRevision
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        model.Session.add(self.pkg1)
        self.pkg1.version = u"First version"
        model.repo.commit_and_remove()

        # edit pkg - PackageRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.notes = u"New notes"
        rev.message = u"Added notes"
        model.repo.commit_and_remove()

        # edit pkg - PackageExtraRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.extras = {u"a": u"b", u"c": u"d"}
        rev.message = u"Added extras"
        model.repo.commit_and_remove()

        # edit pkg - PackageTagRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.add_tag_by_name(u"geo")
        pkg1.add_tag_by_name(u"scientific")
        rev.message = u"Added tags"
        model.repo.commit_and_remove()

        # edit pkg - ResourceRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.resources_all.append(
            model.Resource(
                url=u"http://url1.com",
                format=u"xls",
                description=u"It is.",
                hash=u"abc123",
            )
        )
        rev.message = u"Added resource"
        model.repo.commit_and_remove()

        # edit pkg - ResourceRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.resources_all[0].url = u"http://url1.com/edited"
        pkg1.resources_all.append(model.Resource(url=u"http://url2.com"))
        rev.message = u"Added resource"
        model.repo.commit_and_remove()

        # edit pkg - PackageRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.notes = u"Changed notes"
        rev.message = u"Changed notes"
        model.repo.commit_and_remove()

        self.pkg1 = model.Package.by_name(self.name)
        self.res1 = (
            model.Session.query(model.Resource)
            .filter_by(url=u"http://url1.com/edited")
            .one()
        )
        self.res2 = (
            model.Session.query(model.Resource)
            .filter_by(url=u"http://url2.com")
            .one()
        )
        assert self.pkg1

        assert len(self.pkg1.all_revisions) == 3, self.pkg1.all_revisions
        assert (
            len(self.pkg1.all_related_revisions) == 6
        ), self.pkg1.all_related_revisions
