# encoding: utf-8

from ckan.tests.legacy import CreateTestData
import pytest
import ckan.model as model


class TestRevisionPurge:
    pkgname = u"revision-purge-test"
    old_url = u"abc.com"
    pkgname2 = u"revision-purge-test-2"

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()

        model.repo.new_revision()
        pkg = model.Package(name=self.pkgname)

        pkg.url = self.old_url
        tag1 = model.Tag.by_name(u"russian")
        tag2 = model.Tag.by_name(u"tolstoy")
        pkg.add_tag(tag1)
        pkg.add_tag(tag2)
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        newurl = u"blah.com"
        pkg.url = newurl
        for tag in pkg.get_tags():
            pkg.remove_tag(tag)

        model.Package(name=self.pkgname2)
        model.repo.commit_and_remove()

    def teardown_method(self):
        model.Session.remove()
        pkg_new = model.Package.by_name(self.pkgname2)
        if pkg_new:
            pkg_new.purge()
        pkg = model.Package.by_name(self.pkgname)
        pkg.purge()
        model.Session.commit()
        model.Session.remove()

    def test_1(self):
        rev = model.repo.youngest_revision()
        model.repo.purge_revision(rev, leave_record=True)

        rev = model.repo.youngest_revision()
        pkg = model.Package.by_name(self.pkgname)

        assert rev.message.startswith("PURGED"), rev.message
        assert pkg.url == self.old_url
        pkg2 = model.Package.by_name(self.pkgname2)
        assert pkg2 is None, "pkgname2 should no longer exist"
        assert len(pkg.get_tags()) == 2

    def test_2(self):
        rev = model.repo.youngest_revision()
        num = rev.id
        model.repo.purge_revision(rev, leave_record=True)

        rev = model.repo.youngest_revision()
        # TODO: should youngest_revision be made purge aware
        # (requires state on revision)
        assert rev.id == num

    def test_purge_first_revision(self):
        rev = model.repo.youngest_revision()
        num = rev.id
        q = model.repo.history()
        q = q.order_by(model.Revision.timestamp.desc())
        q = q.limit(2)
        rev2 = q.all()[1]
        model.repo.purge_revision(rev, leave_record=True)

        rev = model.repo.youngest_revision()
        assert rev.id == num
        # either none or should equal num - 2 or be None (if no lower revision)
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.all_revisions) == 1
