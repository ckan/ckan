from datetime import datetime
import difflib
import uuid
import logging
import weakref

from sqlalchemy import *
from sqlalchemy.orm.attributes import get_history, PASSIVE_OFF
from sqlalchemy import __version__ as sqav

from sqla import SQLAlchemyMixin
from sqla import copy_column, copy_table_columns, copy_table

make_uuid = lambda: unicode(uuid.uuid4())
logger = logging.getLogger('vdm')

## -------------------------------------
class SQLAlchemySession(object):
    '''Handle setting/getting attributes on the SQLAlchemy session.
    
    TODO: update all methods so they can take an object as well as session
    object.
    '''

    @classmethod
    def setattr(self, session, attr, value):
        setattr(session, attr, value)
        # check if we are being given the Session class (threadlocal case)
        # if so set on both class and instance
        # this is important because sqlalchemy's object_session (used below) seems
        # to return a Session() not Session
        if isinstance(session, sqlalchemy.orm.scoping.ScopedSession):
            sess = session()
            setattr(sess, attr, value)

    @classmethod
    def getattr(self, session, attr):
        return getattr(session, attr)

    # make explicit to avoid errors from typos (no attribute defns in python!)
    @classmethod
    def set_revision(self, session, revision):
        self.setattr(session, 'HEAD', True)
        self.setattr(session, 'revision', revision)
        if revision.id is None:
            # make uuid here so that if other objects in this session are flushed
            # at the same time they know thier revision id
            revision.id = make_uuid()
            # there was a begin_nested here but that just caused flush anyway.
            session.add(revision)
            session.flush()

    @classmethod
    def get_revision(self, session):
        '''Get revision on current Session/session.
        
        NB: will return None if not set
        '''
        return getattr(session, 'revision', None)

    @classmethod
    def set_not_at_HEAD(self, session):
        self.setattr(session, 'HEAD', False)

    @classmethod
    def at_HEAD(self, session):
        return getattr(session, 'HEAD', True)


## --------------------------------------------------------
## VDM-Specific Domain Objects and Tables

# Enumeration
class State(object):
    ACTIVE = u'active'
    DELETED = u'deleted'
    PENDING = u'pending'
    all = (ACTIVE, DELETED, PENDING)

def make_revision_table(metadata):
    revision_table = Table('revision', metadata,
            Column('id', UnicodeText, primary_key=True, default=make_uuid),
            Column('timestamp', DateTime, default=datetime.utcnow),
            Column('author', String(200)),
            Column('message', UnicodeText),
            Column('state', UnicodeText, default=State.ACTIVE)
            )
    return revision_table


class Revision(SQLAlchemyMixin):
    '''A Revision to the Database/Domain Model.

    All versioned objects have an associated Revision which can be accessed via
    the revision attribute.
    '''
    # TODO:? set timestamp in ctor ... (maybe not as good to have undefined
    # until actual save ...)
    @property
    def __id__(self):
        if self.id is None:
            self.id = make_uuid()
        return self.id
    @classmethod
    def youngest(self, session):
        '''Get the youngest (most recent) revision.

        If session is not provided assume there is a contextual session.
        '''
        q = session.query(self)
        return q.first()


def make_Revision(mapper, revision_table):
    mapper(Revision, revision_table, properties={
        },
        order_by=revision_table.c.timestamp.desc())
    return Revision

## --------------------------------------------------------
## Table Helpers

def make_table_stateful(base_table):
    '''Make a table 'stateful' by adding appropriate state column.'''
    base_table.append_column(
        Column('state', UnicodeText, default=State.ACTIVE)
        )

def make_table_revisioned(base_table):
    logger.warn('make_table_revisioned is deprecated: use make_revisioned_table')
    return make_revisioned_table(base_table)

def make_revisioned_table(base_table):
    '''Modify base_table and create correponding revision table.

    # TODO: (complex) support for complex primary keys on continuity. 
    # Search for "composite foreign key sqlalchemy" for helpful info

    @return revision table.
    '''
    base_table.append_column(
            Column('revision_id', UnicodeText, ForeignKey('revision.id'))
            )
    newtable = Table(base_table.name + '_revision', base_table.metadata,
            )
    copy_table(base_table, newtable)

    # create foreign key 'continuity' constraint
    # remember base table primary cols have been exactly duplicated onto our table
    pkcols = []
    for col in base_table.c:
        if col.primary_key:
            pkcols.append(col)
    if len(pkcols) > 1:
        msg = 'Do not support versioning objects with multiple primary keys'
        raise ValueError(msg)
    fk_name = base_table.name + '.' + pkcols[0].name
    newtable.append_column(
        Column('continuity_id', pkcols[0].type, ForeignKey(fk_name))
        )
    # TODO: a start on composite primary key stuff
    # newtable.append_constraint(
    #        ForeignKeyConstraint(
    #            [c.name for c in pkcols],
    #            [base_table.name + '.' + c.name for c in pkcols ]
    #    ))

    # TODO: why do we iterate all the way through rather than just using dict
    # functionality ...? Surely we always have a revision here ...
    for col in newtable.c:
        if col.name == 'revision_id':
            col.primary_key = True
            newtable.primary_key.columns.add(col)
    return newtable


## --------------------------------------------------------
## Object Helpers

class StatefulObjectMixin(object):
    __stateful__ = True

    def delete(self):
        logger.debug('Running delete on %s', self)
        self.state = State.DELETED
    
    def undelete(self):
        self.state = State.ACTIVE

    def is_active(self):
        # also support None in case this object is not yet refreshed ...
        return self.state is None or self.state == State.ACTIVE


class RevisionedObjectMixin(object):
    __ignored_fields__ = ['revision_id']
    __revisioned__ = True

    @classmethod
    def revisioned_fields(cls):
        table = sqlalchemy.orm.class_mapper(cls).mapped_table
        fields = [ col.name for col in table.c if col.name not in
                cls.__ignored_fields__ ]
        return fields

    def get_as_of(self, revision=None):
        '''Get this domain object at the specified revision.
        
        If no revision is specified revision will be looked up on the global
        session object. If that not found return head.

        get_as_of does most of the crucial work in supporting the
        versioning.
        '''
        sess = object_session(self)
        if revision: # set revision on the session so dom traversal works
            # TODO: should we test for overwriting current session?
            # if rev != revision:
            #     msg = 'The revision on the session does not match the one you' + \
            #     'requesting.'
            #     raise Exception(msg)
            logger.debug('get_as_of: setting revision and not_as_HEAD: %s',
                    revision)
            SQLAlchemySession.set_revision(sess, revision)
            SQLAlchemySession.set_not_at_HEAD(sess)
        else:
            revision = SQLAlchemySession.get_revision(sess)

        if SQLAlchemySession.at_HEAD(sess):
            return self
        else:
            revision_class = self.__revision_class__
            # TODO: when dealing with multi-col pks will need to update this
            # (or just use continuity)
            out = sess.query(revision_class).join('revision').\
                filter(
                    Revision.timestamp <= revision.timestamp
                ).\
                filter(
                    revision_class.id == self.id
                ).\
                order_by(
                    Revision.timestamp.desc()
                )
            return out.first()
    
    @property
    def all_revisions(self):
        allrevs = self.all_revisions_unordered
        ourcmp = lambda revobj1, revobj2: cmp(revobj1.revision.timestamp,
                revobj2.revision.timestamp)
        sorted_revobjs = sorted(allrevs, cmp=ourcmp, reverse=True)
        return sorted_revobjs

    def diff(self, to_revision=None, from_revision=None):
        '''Diff this object returning changes between `from_revision` and
        `to_revision`.

        @param to_revision: revision to diff to (defaults to the youngest rev)
        @param from_revision: revision to diff from (defaults to one revision
        older than to_revision)
        @return: dict of diffs keyed by field name

        e.g. diff(HEAD, HEAD-2) will show diff of changes made in last 2
        commits (NB: no changes may have occurred to *this* object in those
        commits).
        '''
        obj_rev_class = self.__revision_class__
        sess = object_session(self)
        obj_rev_query = sess.query(obj_rev_class).join('revision').\
                        filter(obj_rev_class.id==self.id).\
                        order_by(Revision.timestamp.desc())
        obj_class = self
        to_obj_rev, from_obj_rev = self.get_obj_revisions_to_diff(\
            obj_rev_query,
            to_revision=to_revision,
            from_revision=from_revision)
        return self.diff_revisioned_fields(to_obj_rev, from_obj_rev,
                                           obj_class)

    
    def get_obj_revisions_to_diff(self, obj_revision_query, to_revision=None,
                           from_revision=None):
        '''Diff this object returning changes between `from_revision` and
        `to_revision`.

        @param obj_revision_query: query of all object revisions related to
        the object being diffed. e.g. all PackageRevision objects with 
        @param to_revision: revision to diff to (defaults to the youngest rev)
        @param from_revision: revision to diff from (defaults to one revision
        older than to_revision)
        @return: dict of diffs keyed by field name

        e.g. diff(HEAD, HEAD-2) will show diff of changes made in last 2
        commits (NB: no changes may have occurred to *this* object in those
        commits).
        '''
        sess = object_session(self)
        if to_revision is None:
            to_revision = Revision.youngest(sess)
        out = obj_revision_query.\
              filter(Revision.timestamp<=to_revision.timestamp)
        to_obj_rev = out.first()
        if not from_revision:
            from_revision = sess.query(Revision).\
                filter(Revision.timestamp<to_revision.timestamp).first()
        # from_revision may be None, e.g. if to_revision is rev when object was
        # created
        if from_revision:
            out = obj_revision_query.\
                filter(Revision.timestamp<=from_revision.timestamp)
            from_obj_rev = out.first()
        else:
            from_obj_rev = None
        return to_obj_rev, from_obj_rev
    
    @classmethod
    def diff_revisioned_fields(self, to_obj_rev, from_obj_rev, obj_class):
        '''
        Given two object revisions (e.g. PackageRevisions), diffs the
        revisioned fields.
        @to_obj_rev final object revision to diff
        @from_obj_rev original object revision to diff
        @param obj_class: class of object
        @return dict of the diffs, keyed by the field names
        '''
        diffs = {}
        fields = obj_class.revisioned_fields()

        for field in fields:
            # allow None on getattr since rev may be None (see above)
            values = [getattr(obj_rev, field, None) for obj_rev in [from_obj_rev, to_obj_rev]]
            diff = self._differ(values[0], values[1])
            if diff:
                diffs[field] = diff
        return diffs

    @classmethod
    def _differ(self, str_a, str_b):
        str_a = unicode(str_a)
        str_b = unicode(str_b)
        if str_a != str_b:
            return '\n'.join(difflib.Differ().compare(str_a.split('\n'), str_b.split('\n')))
        else:
            return None



## --------------------------------------------------------
## Mapper Helpers

import sqlalchemy.orm.properties
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm import relation, backref

def modify_base_object_mapper(base_object, revision_obj, state_obj):
    base_mapper = class_mapper(base_object)
    base_mapper.add_property('revision', relation(revision_obj))

def create_object_version(mapper_fn, base_object, rev_table):
    '''Create the Version Domain Object corresponding to base_object.

    E.g. if Package is our original object we should do::
    
        # name of Version Domain Object class 
        PackageVersion = create_object_version(..., Package, ...)
    
    NB: This must obviously be called after mapping has happened to
    base_object.
    '''
    # TODO: can we always assume all versioned objects are stateful?
    # If not need to do an explicit check
    class MyClass(StatefulObjectMixin, SQLAlchemyMixin):
        pass

    name = base_object.__name__ + 'Revision'
    MyClass.__name__ = name
    MyClass.__continuity_class__ = base_object

    # Must add this so base object can retrieve revisions ...
    base_object.__revision_class__ = MyClass

    ourmapper = mapper_fn(MyClass, rev_table, properties={
        # NB: call it all_revisions_... rather than just revisions_... as it
        # will yield all revisions not just those less than the current
        # revision
        'continuity':relation(base_object,
            backref=backref('all_revisions_unordered',
                cascade='all, delete, delete-orphan'),
                order_by=rev_table.c.revision_id.desc()
            ),
        # 'continuity':relation(base_object),
        },
        order_by=[rev_table.c.continuity_id, rev_table.c.revision_id.desc()]
        )
    base_mapper = class_mapper(base_object)
    # add in 'relationship' stuff from continuity onto revisioned obj
    # 3 types of relationship
    # 1. scalar (i.e. simple fk)
    # 2. list (has many) (simple fk the other way)
    # 3. list (m2m) (join table)
    # 
    # Also need to check whether related object is revisioned
    # 
    # If related object is revisioned then can do all of these
    # If not revisioned can only support simple relation (first case -- why?)
    for prop in base_mapper.iterate_properties:
        try:
            is_relation = prop.__class__ == sqlalchemy.orm.properties.PropertyLoader
        except AttributeError:
            # SQLAlchemy 0.9
            is_relation = prop.__class__ == sqlalchemy.orm.properties.RelationshipProperty

        if is_relation:
            # in sqlachemy 0.4.2
            # prop_remote_obj = prop.select_mapper.class_
            # in 0.4.5
            prop_remote_obj = prop.argument
            remote_obj_is_revisioned = getattr(prop_remote_obj, '__revisioned__', False)
            # this is crude, probably need something better
            is_many = (prop.secondary != None or prop.uselist)
            if remote_obj_is_revisioned:
                propname = prop.key
                add_fake_relation(MyClass, propname, is_many=is_many)
            elif not is_many:
                ourmapper.add_property(prop.key, relation(prop_remote_obj))
            else:
                # TODO: actually deal with this
                # raise a warning of some kind
                msg = 'Skipping adding property %s to revisioned object' % prop
                # Issue #3 not considered for over two years, so removing this
                # annoying log message.
                # This doesn\'t seem to be a problem for ckan.
                #logger.info(msg)

    return MyClass

def add_fake_relation(revision_class, name, is_many=False): 
    '''Add a 'fake' relation on ObjectRevision objects.
    
    These relation are fake in that they just proxy to the continuity object
    relation.
    '''
    def _pget(self):
        related_object = getattr(self.continuity, name)
        if is_many:
            # do not need to do anything to get to right revision since either
            # 1. this is implemented inside the is_many relation we proxy to
            # (as is the case with StatefulLists and assoc proxy setup as used
            # in add_stateful_versioned_m2m)
            # 2. it is not because it is not appropriate to apply it
            # (e.g. package.package_tags which points to PackageTag objects and
            # which is not versioned here ...)
            return related_object
        else:
            return related_object.get_as_of()
    x = property(_pget)
    setattr(revision_class, name, x)

from stateful import add_stateful_m2m
def add_stateful_versioned_m2m(*args, **kwargs):
    '''Add a Stateful versioned m2m attributes to a domain object.
    
    For args and kwargs see add_stateful_m2m.
    '''
    def get_as_of(obj):
        return obj.get_as_of()

    newkwargs = dict(kwargs)
    newkwargs['base_modifier'] = get_as_of
    add_stateful_m2m(*args, **newkwargs)

def add_stateful_versioned_m2m_on_version(revision_class, m2m_property_name):
    # just add these m2m properties to version
    active_name = m2m_property_name + '_active'
    deleted_name = m2m_property_name + '_deleted'
    for propname in [active_name, deleted_name, m2m_property_name]:
        add_fake_relation(revision_class, propname,
                is_many=True)


from sqlalchemy.orm import MapperExtension
from sqlalchemy.orm import object_session
from sqlalchemy.orm import EXT_CONTINUE

class Revisioner(MapperExtension):
    '''SQLAlchemy MapperExtension which implements revisioning of sqlalchemy
    mapped objects.
    
    In essence it implements copy on write.

    However various additional features such as:
    
        * Checking for 'real' changes -- often sqlalchemy objects are marked as
          changed when not (just a related attribute has changed).
        * support for ignored attributes (these attributes will be ignored when
          checking for changes and creating new revisions of the object)
    '''

    def __init__(self, revision_table):
        self.revision_table = revision_table
        # Sometimes (not predictably) the after_update method is called
        # *after* the next instance's before_update! So to avoid this,
        # we store the instance with the is_changed flag.
        # It is a weak key dictionary to make sure the instance is garbage
        # collected.
        self._is_changed = weakref.WeakKeyDictionary() # instance:is_changed

    def revisioning_disabled(self, instance):
        # logger.debug('revisioning_disabled: %s' % instance)
        sess = object_session(instance)
        disabled = getattr(sess, 'revisioning_disabled', False)
        return disabled

    def set_revision(self, instance):
        sess = object_session(instance)
        current_rev = SQLAlchemySession.get_revision(sess) 
        # was using revision_id but this led to weird intermittent erros
        # (1/3: fail on first item, 1/3 on second, 1/3 ok).
        # assert current_rev.id
        # instance.revision_id = current_rev.id
        # LATER: this resulted (I think) from setting revision_id but not
        # setting revision on the object

        # In fact must do *both* Why?
        # SQLAlchemy mapper extension methods can only make changes to columns.
        # Any changes make to relations will not be picked up (from docs):
        # "Column-based attributes can be modified within this method which will
        # result in their being updated. However no changes to the overall
        # flush plan can be made; this means any collection modification or
        # save() operations which occur within this method will not take effect
        # until the next flush call."
        #
        # Thus: set revision_id to ensure that value is saved
        # set revision to ensure object behaves how it should (e.g. we use
        # instance.revision in after_update)
        assert current_rev, 'No revision is currently set for this Session'
        # We need the revision id unfortunately for this all to work
        # Why? We cannot created new sqlachemy objects in here (as they won't
        # get saved). This means we have to created revision_object directly in
        # database which requires we use *column* values. In particular, we
        # need revision_id not revision object to create revision_object
        # properly!
        logger.debug('Revisioner.set_revision: revision is %s', current_rev)
        assert current_rev.id, 'Must have a revision.id to create object revision'
        instance.revision = current_rev
        # must set both since we are already in flush so setting object will
        # not be enough
        instance.revision_id = current_rev.id

    def check_real_change(self, instance, mapper, connection):
        # check each attribute to see if they have been changed
        logger.debug('check_real_change: %s', instance)
        if sqav.startswith("0.4"):
            state = instance._state
        else:
            state = instance
        for key in instance.revisioned_fields():
            (added, unchanged, deleted) = get_history(state,
                                                      key,
                                                      passive = PASSIVE_OFF)
            if added or deleted:
                logger.debug('check_real_change: True')
                return True
        logger.debug('check_real_change: False')
        return False

    def make_revision(self, instance, mapper, connection):
        # NO GOOD working with the object as that only gets committed at next
        # flush. Need to work with the table directly
        colvalues = {}
        table = mapper.tables[0]
        for key in table.c.keys():
            val = getattr(instance, key)
            colvalues[key] = val
        # because it is unlikely instance has been refreshed at this point the
        # fk revision_id is not yet set on this object so get it directly
        assert instance.revision.id
        colvalues['revision_id'] = instance.revision.id
        colvalues['continuity_id'] = instance.id

        # Allow for multiple SQLAlchemy flushes/commits per VDM revision
        revision_already_query = self.revision_table.count()
        existing_revision_clause = and_(
                self.revision_table.c.continuity_id == instance.id,
                self.revision_table.c.revision_id == instance.revision.id)
        revision_already_query = revision_already_query.where(
                existing_revision_clause
                )
        num_revisions = connection.execute(revision_already_query).scalar()
        revision_already = num_revisions > 0

        if revision_already:
            logger.debug('Updating version of %s: %s', instance, colvalues)
            connection.execute(self.revision_table.update(existing_revision_clause).values(colvalues))
        else:
            logger.debug('Creating version of %s: %s', instance, colvalues)
            ins = self.revision_table.insert().values(colvalues)
            connection.execute(ins)

        # set to None to avoid accidental reuse
        # ERROR: cannot do this as after_* is called per object and may be run
        # before_update on other objects ...
        # probably need a SessionExtension to deal with this properly
        # object_session(instance).revision = None

    def before_update(self, mapper, connection, instance):
        self._is_changed[instance] = self.check_real_change(instance, mapper, connection)
        if not self.revisioning_disabled(instance) and self._is_changed[instance]:
            logger.debug('before_update: %s', instance)
            self.set_revision(instance)
            self._is_changed[instance] = self.check_real_change(
                instance, mapper, connection)
        return EXT_CONTINUE

    # We do most of the work in after_insert/after_update as at that point
    # instance has been properly created (which means e.g. instance.id is
    # available ...)
    def before_insert(self, mapper, connection, instance):
        self._is_changed[instance] = self.check_real_change(instance, mapper, connection)
        if not self.revisioning_disabled(instance) and self._is_changed[instance]:
            logger.debug('before_insert: %s', instance)
            self.set_revision(instance)
        return EXT_CONTINUE

    def after_update(self, mapper, connection, instance):
        if not self.revisioning_disabled(instance) and self._is_changed[instance]:
            logger.debug('after_update: %s', instance)
            self.make_revision(instance, mapper, connection)
        return EXT_CONTINUE

    def after_insert(self, mapper, connection, instance):
        if not self.revisioning_disabled(instance) and self._is_changed[instance]:
            logger.debug('after_insert: %s', instance)
            self.make_revision(instance, mapper, connection)
        return EXT_CONTINUE

    def append_result(self, mapper, selectcontext, row, instance, result,
             **flags):
        # TODO: 2009-02-13 why is this needed? Can we remove this?
        return EXT_CONTINUE

