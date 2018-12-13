'''A simple demo of vdm.

This demo shows how to use vdm for simple versioning of individual domain
objects (without any versioning of the relations between objects). For more
complex example see demo.py
'''

from sqlalchemy import *
# SQLite is not as reliable/demanding as postgres but you can use it
engine = create_engine('postgres://tester:pass@localhost/vdmtest')

from demo_meta import Session, metadata, init_with_engine
init_with_engine(engine)

# import the versioned domain model package
import vdm.sqlalchemy

## -----------------------------
## Our Tables

# NB: you really need to set up your tables and domain object separately for
# vdm

wikipage = Table('wikipage', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Unicode(200)),
    Column('body', UnicodeText),
    )

# -----------------------------
# VDM stuff

# Now we need some standard VDM tables
state_table = vdm.sqlalchemy.make_state_table(metadata)
revision_table = vdm.sqlalchemy.make_revision_table(metadata)


# Make our original table vdm-ready by adding state to it
vdm.sqlalchemy.make_table_stateful(wikipage)
# And create the table for the wikipage revisions/versions 
wikipage_revision = vdm.sqlalchemy.make_table_revisioned(wikipage)


## ------------------------------
## Our Domain Objects

# Suppose your class started out as 
# Class WikiPage(object):
#    pass
#
# then to make it versioned you just need to add in some Mixins

class WikiPage(
    vdm.sqlalchemy.StatefulObjectMixin, # make it state aware
    vdm.sqlalchemy.RevisionedObjectMixin, # make it versioned aware
    vdm.sqlalchemy.SQLAlchemyMixin # this is optional (provides nice __str__)
    ):

    pass


## Let's map the tables to the domain objects
mapper = Session.mapper

# VDM-specific domain objects
State = vdm.sqlalchemy.make_State(mapper, state_table)
Revision = vdm.sqlalchemy.make_Revision(mapper, revision_table)


# Now our domain object.
# This is just like any standard sqlalchemy mapper setup
# The only addition is  the mapper extension
mapper(WikiPage, wikipage, properties={
    },
    # mapper extension which handles automatically versioning the object
    extension=vdm.sqlalchemy.Revisioner(wikipage_revision)
    )
# add the revision and state attributes into WikiPage
vdm.sqlalchemy.modify_base_object_mapper(WikiPage, Revision, State)

# Last: create domain object corresponding to the Revision/Version of the main
# object
WikiPageRevision = vdm.sqlalchemy.create_object_version(
        mapper,
        WikiPage,
        wikipage_revision
        )

# We recommend you use the Repository object to manage your versioned domain
# objects
# This isn't required but it provides extra useful features such as purging
# See the module for full details
from vdm.sqlalchemy.tools import Repository
repo = Repository(metadata, Session, versioned_objects=[WikiPage])


# Let's try it out
def test_it():
    # clean out the db so we start clean
    repo.rebuild_db()

    # you need to set up a Revision for versioned objects to use
    # this is set on the SQLAlchemy session so as to be available generally
    # It can be set up any time before you commit but it is usually best to do
    # it before you start creating or modifying versioned objects

    # You can set up the revision directly e.g.
    # rev = Revision()
    # SQLAlchemySession.set_revision(rev)
    # (or even just Session.revision = rev)
    # However this will do the same and is simpler
    rev = repo.new_revision()

    # now make some changes
    mypage = WikiPage(name=u'Home', body=u'Some text')
    mypage2 = WikiPage(name=u'MyPage', body=u'')
    # let's add a log message to these changes
    rev.message = u'My first revision'
    # Just encapsulates Session.commit() + Session.remove()
    # (with some try/excepts)
    repo.commit_and_remove()

    last_revision = repo.youngest_revision()
    assert last_revision.message == u'My first revision'
    outpage = WikiPage.query.filter_by(name=u'Home').first()
    assert outpage and outpage.body == u'Some text'

    # let's make some more changes

