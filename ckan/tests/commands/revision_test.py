from ckan.tests import *

import ckan.commands.revision

import ckan.model as model

class _TestRevisionPurge:
    
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def setup_method(self, name=''):
        self.pkgname = 'revision-purge-test'

        model.repo.begin()
        self.pkg = model.Package(name=self.pkgname)
        self.old_url = 'abc.com'
        self.pkg.url = self.old_url
        tag1 = model.Tag.by_name('russian')
        tag2 = model.Tag.by_name('tolstoy')
        self.pkg.tags.append(tag1)
        self.pkg.tags.append(tag2)
        model.repo.commit()

        txn2 = model.repo.begin_transaction()
        pkg = model.Package.by_name(self.pkgname)
        newurl = 'blah.com'
        pkg.url = newurl
        pkg.tags = []
        self.pkgname2 = 'revision-purge-test-2'
        self.pkg_new = model.Package(name=self.pkgname2)
        model.repo.commit()

    def teardown_method(self, name=''):
        try:
            self.pkg_new.purge()
        except:
            pass
        self.pkg.purge()

    def test_1(self):
        rev = self.repo.youngest_revision()
        cmd = ckan.commands.revision.PurgeRevision(rev, leave_record=True)
        cmd.execute()

        rev = self.repo.youngest_revision()
        pkg = rev.model.packages.get(self.pkgname)

        assert rev.log_message == 'PURGED'
        assert len(pkg.tags) == 2
        assert pkg.url == self.old_url
        try:
            rev.model.package.get(self.pkgname2)
            assert False, 'Should have raised an exception'
        except:
            pass

    def test_2(self):
        rev = self.repo.youngest_revision()
        num = rev.id
        cmd = ckan.commands.revision.PurgeRevision(rev, leave_record=False)
        cmd.execute()

        rev = self.repo.youngest_revision()
        assert rev.id < num

    def test_purge_first_revision(self):
        rev = self.repo.youngest_revision()
        num = rev.id
        rev2 = self.repo.get_revision(rev.id - 1)
        cmd = ckan.commands.revision.PurgeRevision(rev2, leave_record=False)
        cmd.execute()

        rev = self.repo.youngest_revision()
        assert rev.id == num
        # either none or should equal num - 2 or be None (if no lower revision)
        if rev.base_revision != None:
            baseid = rev.base_revision.id
            # cannot use == and as no guarantee next one down is only 2 below
            # however suspicious if 1 ...
            assert baseid <= num - 2 and baseid > 1
        pkg = rev.model.packages.get(self.pkgname)
        assert len(pkg.history) == 1

