# many of the tests are in demo_test as that sets up nice fixtures
from tools import *

dburi = 'postgres://tester:pass@localhost/vdmtest'
from demo import *
class TestRepository:
    repo = Repository(metadata, Session, dburi)

    def test_transactional(self):
        assert self.repo.have_scoped_session
        assert self.repo.transactional

    def test_init_vdm(self):
        self.repo.session.remove()
        self.repo.clean_db()
        self.repo.create_db()
        self.repo.init_db()
        # nothing to test at the moment ...

    def test_new_revision(self):
        self.repo.session.remove()
        rev = self.repo.new_revision()
        assert rev is not None

    def test_history(self):
        self.repo.session.remove()
        self.repo.rebuild_db()
        rev = self.repo.new_revision()
        rev.message = u'abc'
        self.repo.commit_and_remove()
        history = self.repo.history()
        revs = history.all()
        assert len(revs) == 1

