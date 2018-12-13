'''Various useful tools for working with Versioned Domain Models.

Primarily organized within a `Repository` object.
'''
from sqlalchemy import MetaData

import logging
logger = logging.getLogger('vdm')

# fix up table dropping on postgres
# http://blog.pythonisito.com/2008/01/cascading-drop-table-with-sqlalchemy.html
from sqlalchemy import __version__ as sqav
if sqav[:3] in ("0.4", "0.5"):
     from sqlalchemy.databases import postgres
     class CascadeSchemaDropper(postgres.PGSchemaDropper):
          def visit_table(self, table):
               for column in table.columns:
                    if column.default is not None:
                         self.traverse_single(column.default)
               self.append("\nDROP TABLE " +
                           self.preparer.format_table(table) +
                           " CASCADE")
               self.execute()
     postgres.dialect.schemadropper = CascadeSchemaDropper

elif sqav[:3] in ("0.6", "0.7", "0.8", "0.9", "1.0", "1.1"):
     from sqlalchemy.dialects.postgresql import base
     def visit_drop_table(self, drop):
          return "\nDROP TABLE " + \
                 self.preparer.format_table(drop.element) + \
                 " CASCADE"
     base.dialect.ddl_compiler.visit_drop_table = visit_drop_table
else:
     raise ValueError("VDM only works with SQLAlchemy versions 0.4 through 0.9, not: %s" % sqav)


from sqlalchemy import create_engine
try:
    from sqlalchemy.orm import ScopedSession as scoped_session
except ImportError:
    from sqlalchemy.orm import scoped_session

from sqlalchemy.orm import class_mapper
from sqlalchemy.orm import object_session
from sqlalchemy import __version__ as sqla_version

from base import SQLAlchemySession, State, Revision

class Repository(object):
    '''Manage repository-wide type changes for versioned domain models.

    For example:
        * creating, cleaning and initializing the repository (DB).
        * purging revisions
    '''
    def __init__(self, our_metadata, our_session, versioned_objects=None, dburi=None):
        '''
        @param versioned_objects: list of classes of objects which are
        versioned (NB: not the object *versions* but the continuity objects
        themselves). Needed because this will vary from vdm to vdm.
        @param dburi: sqlalchemy dburi. If supplied will create engine and bind
        it to metadata and session.
        '''
        self.metadata = our_metadata
        self.session = our_session
        self.versioned_objects = versioned_objects
        self.dburi = dburi
        self.have_scoped_session = isinstance(self.session, scoped_session)
        self.transactional = False
        if self.have_scoped_session:
            tmpsess = self.session()
        else:
            tmpsess = self.session
        if sqla_version > '0.4.99':
            self.transactional = not tmpsess.autocommit
        else:
            self.transactional = tmpsess.transactional
        if self.dburi:
            engine = create_engine(dburi, pool_threadlocal=True)
            self.metadata.bind = engine
            self.session.bind = engine

    def create_db(self):
        logger.info('Creating DB')
        self.metadata.create_all(bind=self.metadata.bind)

    def clean_db(self):
        logger.info('Cleaning DB')
        self.metadata.drop_all(bind=self.metadata.bind)

    def rebuild_db(self):
        logger.info('Rebuilding DB')
        self.clean_db()
        self.session.remove()
        self.init_db()

    def init_db(self):
        self.create_db()
        logger.info('Initing DB')
        self.session.remove()

    def commit(self):
        '''Commit/flush (as appropriate) the Sqlalchemy session.'''
        # TODO: should we do something like set the revision state as well ...
        if self.transactional:
            try:
                self.session.commit()
            except:
                self.session.rollback()
                # should we remove?
                self.session.remove()
                raise
        else:
            self.session.flush()

    def commit_and_remove(self):
        self.commit()
        self.session.remove()

    def new_revision(self):
        '''Convenience method to create new revision and set it on session.

        NB: if in transactional mode do *not* need to call `begin` as we are
        automatically within a transaction at all times if session was set up
        as transactional (every commit is paired with a begin)
        <http://groups.google.com/group/sqlalchemy/browse_thread/thread/a54ce150b33517db/17587ca675ab3674>
        '''
        rev = Revision()
        self.session.add(rev)
        SQLAlchemySession.set_revision(self.session, rev)
        return rev

    def youngest_revision(self):
        '''Get the youngest (most recent) revision.'''
        q = self.history()
        q = q.order_by(Revision.timestamp.desc())
        return q.first()

    def history(self):
        '''Return a history of the repository as a query giving all active revisions.

        @return: sqlalchemy query object.
        '''
        return self.session.query(Revision).filter_by(state=State.ACTIVE)

    def list_changes(self, revision):
        '''List all objects changed by this `revision`.

        @return: dictionary of changed instances keyed by object class.
        '''
        results = {}
        for o in self.versioned_objects:
            revobj = o.__revision_class__
            items = self.session.query(revobj).filter_by(revision=revision).all()
            results[o] = items
        return results

    def purge_revision(self, revision, leave_record=False):
        '''Purge all changes associated with a revision.

        @param leave_record: if True leave revision in existence but change message
            to "PURGED: {date-time-of-purge}". If false delete revision object as
            well.

        Summary of the Algorithm
        ------------------------

        1. list all RevisionObjects affected by this revision
        2. check continuity objects and cascade on everything else ?
            1. crudely get all object revisions associated with this
            2. then check whether this is the only revision and delete the
            continuity object

            3. ALTERNATIVELY delete all associated object revisions then do a
            select on continutity to check which have zero associated revisions
            (should only be these ...)
        '''
        logger.debug('Purging revision: %s' % revision.id)
        to_purge = []
        SQLAlchemySession.setattr(self.session, 'revisioning_disabled', True)
        self.session.autoflush = False
        for o in self.versioned_objects:
            revobj = o.__revision_class__
            items = self.session.query(revobj).filter_by(revision=revision).all()
            for item in items:
                continuity = item.continuity

                if continuity.revision == revision: # need to change continuity
                    trevobjs = self.session.query(revobj).join('revision').  filter(
                            revobj.continuity==continuity
                            ).order_by(Revision.timestamp.desc()).limit(2).all()
                    if len(trevobjs) == 0:
                        raise Exception('Should have at least one revision.')
                    if len(trevobjs) == 1:
                        to_purge.append(continuity)
                    else:
                        new_correct_revobj = trevobjs[1] # older one
                        self.revert(continuity, new_correct_revobj)
                # now delete revision object
                self.session.delete(item)
            for cont in to_purge:
                self.session.delete(cont)
        if leave_record:
            import datetime
            revision.message = u'PURGED: %s UTC' % datetime.datetime.utcnow()
        else:
            self.session.delete(revision)
        self.commit_and_remove()

    def revert(self, continuity, new_correct_revobj):
        '''Revert continuity object back to a particular revision_object.

        NB: does *not* call flush/commit.
        '''
        logger.debug('revert: %s' % continuity)
        table = class_mapper(continuity.__class__).mapped_table
        # TODO: ? this will only set columns and not mapped attribs
        # TODO: need to do this directly on table or disable
        # revisioning behaviour ...
        for key in table.c.keys():
            value = getattr(new_correct_revobj, key)
            # logger.debug('%s::%s' % (key, value))
            # logger.debug('old: %s' % getattr(continuity, key))
            setattr(continuity, key, value)
        logger.debug('revert: end: %s' % continuity)
        logger.debug(object_session(continuity))
        logger.debug(self.session)

