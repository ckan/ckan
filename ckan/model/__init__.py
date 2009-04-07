from core import *
from apikey import apikey_table, ApiKey
from extras import Extra, extra_table

from license import LicenseList
license_names = LicenseList.all_formatted


class Repository(vdm.sqlalchemy.Repository):

    def init_db(self):
        super(Repository, self).init_db()
        for name in license_names:
            if not License.by_name(name):
                License(name=name)
        if Revision.query.count() == 0:
            rev = Revision()
            rev.author = 'system'
            rev.message = u'Initialising the Repository'
        self.commit_and_remove()

    def begin_transaction(self):
        # do *not* call begin again as we are automatically within a
        # transaction at all times as session was set up as transactional
        # (every commit is paired with a begin)
        # <http://groups.google.com/group/sqlalchemy/browse_thread/thread/a54ce150b33517db/17587ca675ab3674>
        # Session.begin()
        rev = new_revision()
        self.revision = rev
        return rev

    def begin(self):
        return self.begin_transaction()

    def commit(self):
        self.revision = None
        try:
            Session.commit()
        except:
            Session.rollback()
            Session.remove()
            raise

    def history(self):
        active = State.query.filter_by(name='active').one()
        return Revision.query.filter_by(state=active).all()

    def youngest_revision(self):
        return Revision.youngest()

repo = Repository(metadata, Session,
        versioned_objects=[Package, PackageTag]
        )

# TODO: move this onto the repo object
def create_db():
    repo.create_db()

def init_db():
    repo.init_db()

def rebuild_db():
    repo.rebuild_db()

def new_revision():
    return repo.new_revision()

