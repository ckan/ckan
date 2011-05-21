from ckan.tests import *

import ckan.model as model

class TestRevisionPurge:
    
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def setup(self):
        self.pkgname = u'revision-purge-test'

        model.repo.new_revision()
        self.pkg = model.Package(name=self.pkgname)
        self.old_url = u'abc.com'
        self.pkg.url = self.old_url
        tag1 = model.Tag.by_name(u'russian')
        tag2 = model.Tag.by_name(u'tolstoy')
        self.pkg.tags.append(tag1)
        self.pkg.tags.append(tag2)
        model.repo.commit_and_remove()

        txn2 = model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        newurl = u'blah.com'
        pkg.url = newurl
        pkg.tags = []
        self.pkgname2 = u'revision-purge-test-2'
        self.pkg_new = model.Package(name=self.pkgname2)
        model.repo.commit_and_remove()

    def teardown(self):
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

        assert rev.message.startswith('PURGED'), rev.message
        assert pkg.url == self.old_url
        pkg2 = model.Package.by_name(self.pkgname2)
        assert pkg2 is None, 'pkgname2 should no longer exist'
        assert len(pkg.tags) == 2

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

