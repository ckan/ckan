"""
Sub-domain model for distributed data version control.
"""
from meta import *
import vdm.sqlalchemy
from ckan.model.core import DomainObject
from ckan.model import Session, Revision, Package, Tag, Group
from ckan.model import setup_default_user_roles
from simplejson import dumps, loads
import datetime
import uuid

class ConflictException(Exception): pass
class SequenceException(Exception): pass
class TipAtHeadException(Exception): pass
class ChangesSourceException(Exception): pass
class UncommittedChangesException(Exception): pass
class EmptyChangesetRegisterException(Exception): pass


class ChangesetLayerBase(object):

    def dumps(self, data):
        try:
            json = dumps(data, indent=2)
        except Exception, inst:
            msg = "Couldn't convert to JSON: %s" % data
            raise Exception, "%s: %s" % (msg, inst)
        return json

    dumps = classmethod(dumps)

    def loads(self, json):
        try:
            data = loads(json)
        except Exception, inst:
            msg = "Couldn't parse JSON: %s" % json
            raise Exception, "%s: %s" % (msg, inst)
        return data

    loads = classmethod(loads)


class ChangesetDomainObject(DomainObject, ChangesetLayerBase): pass


class Changeset(ChangesetDomainObject):
   
    STATUS_CONSTRUCTED = u'constructed'
    STATUS_QUEUED = u'queued'
    STATUS_APPLIED = u'applied'
    STATUS_IGNORED = u'ignored'
    STATUS_BROKEN = u'broken'

    def get_meta(self):
        return self.loads(self.meta or "{}")

    def set_meta(self, meta_data):
        self.meta = unicode(self.dumps(meta_data))

    def apply(self, is_forced=False, report={}):
        meta = self.get_meta()
        register = ChangesetRegister()
        Session.add(self) # Otherwise self.changes db lazy-load doesn't work.
        revision_id = register.apply_changes(self.changes, 
            meta=meta, report=report, is_forced=is_forced)
        self.revision_id = revision_id
        self.status = self.STATUS_APPLIED
        # Todo: Session rollback on error.
        Session.commit()
        register.move_tip(self.id)
        return self.revision_id

    def is_conflicting(self):
        try:
            self.detect_conflict()
        except ConflictException:
            return True
        else:
            return False

    def detect_conflict(self):
        for change in self.changes:
            change.detect_conflict()

    def as_dict(self):
        meta_data = self.get_meta()
        changes_data = [c.as_dict() for c in self.changes]
        changeset_data = {
            'id': self.id,
            'closes_id': self.closes_id,
            'follows_id': self.follows_id,
            'meta': meta_data,
            'timestamp': self.timestamp.isoformat(),
            'changes': changes_data,
        }
        return changeset_data


class Change(ChangesetDomainObject):

    registers = {}

    def detect_conflict(self):
        register, key = self.deref()
        register.detect_conflict(key, self.as_vector())

    def apply(self, is_forced=False):
        if not is_forced:
            self.detect_conflict()
        register, key = self.deref()
        vector = self.as_vector()
        entity = register.get(key, None)
        if vector.old == None:
            # Create.
            if entity != None:
                msg = "Can't apply creating change, since entity already exists for ref: %s" % self.ref
                raise Exception, msg
            entity = register.create_entity(key)
            register.patch(entity, vector)
        elif vector.new == None:
            # Delete.
            if entity == None:
                msg = "Can't apply deleting change, since entity not found for ref: %s" % self.ref
                raise Exception, msg
            raise Exception, "Sorry, appling a deleting changeset isn't supported yet."
            # Todo: Delete method on register class.
            #entity = register.delete(key)
        else:
            # Update.
            if entity == None:
                msg = "Can't apply updating change, since entity not found for ref: %s" % self.ref
                raise Exception, msg
            entity = register.get(key)
            register.patch(entity, vector)
        return entity # keep in scope?

    def as_vector(self):
        data = self.load_diff()
        return Vector(data['old'], data['new'])

    def load_diff(self):
        return self.loads(self.diff)

    def deref(self):
        parts = self.ref.split('/')
        register_type = parts[1]
        register_key = parts[2]
        if register_type in self.registers:
            register_class = self.registers[register_type]
            register = register_class()
            return (register, register_key)
        else:
            raise Exception, "Can't deref '%s' with register map: %s" % (self.ref, self.registers)

    def as_dict(self):
        change_data = {}
        change_data['ref'] = self.ref
        change_data['diff'] = self.load_diff()
        return change_data

    def get_old(self):
        return self.as_vector().old

    old = property(get_old)

    def get_new(self):
        return self.as_vector().new

    new = property(get_new)


class Vector(object):

    def __init__(self, old, new):
        self.old = old
        self.new = new

    def as_diff(self):
        data = {
            'old': self.old,
            'new': self.new,
        } 
        return unicode(ChangesetLayerBase().dumps(data))


class ChangeArithmetic(object):

    def calc_changes(self):
        sequence = self.get_sequence()
        cache = {}
        for changes in sequence:
            for change in changes:
                if change.ref not in cache:
                    cache[change.ref] = Vector(change.old, change.new)
                vector = cache[change.ref]
                # Oldest old value...
                if vector.old != None:
                    for name, value in change.old.items():
                        if name not in vector.old:
                            vector.old[name] = value
                # ...and newest new value.
                if vector.new == None or change.new == None:
                    vector.new = change.new
                elif change.new != None:
                    for name, value in change.new.items():
                        vector.new[name] = value
        changes = []
        for ref, vector in cache.items():
            diff = vector.as_diff()
            change = Change(ref=ref, diff=diff)
            changes.append(change)
        return changes

    def get_sequence(self):
        raise Exception, "Method not implemented."


class Range(ChangeArithmetic):

    def __init__(self, start, stop):
        self.start = start   # Changeset instance.
        self.stop = stop     # Changeset instance.
        self.sequence = None # List of Change instances.
        self.changesets = None # List of Changeset instances

    def is_broken(self):
        try:
            self.get_changesets()
        except SequenceException:
            return True
        else:
            return False

    def get_changesets(self):
        if self.changesets == None:
            parentage = Parentage(self.stop)
            self.changesets = [self.stop]
            changeset = self.stop
            while(changeset.id != self.start.id):
                changeset = parentage.next()
                if changeset == None:
                    msg = "Changeset %s does not follow changeset %s." % (self.stop.id, self.start.id)
                    raise SequenceException, msg
                self.changesets.append(changeset)
            self.changesets.reverse()
        return self.changesets

    def get_sequence(self):
        if self.sequence == None:
            self.sequence = []
            for changeset in self.get_changesets():
                self.sequence.append(changeset.changes)
        return self.sequence

    def pop_first(self):  # Todo: Rework as 'exclude_start' parameter.
        sequence = self.get_sequence()
        return sequence.pop(0)


class CommonAncestor(ChangeArithmetic):

    def __init__(self, child1, child2):
        self.child1 = child1
        self.child2 = child2

    def find(self):
        # Optimised for performance. Alternates between steping back through
        # one line of changes looking for last item in other line of changes.
        parentage1 = Parentage(self.child1)
        parentage2 = Parentage(self.child2)
        pointer1 = self.child1
        pointer2 = self.child2
        line1 = [self.child1]
        line2 = [self.child2]
        while(pointer1 or pointer2):
            if pointer1:
                for item2 in line2:
                    if pointer1.id == item2.id:
                        return pointer1
                pointer1 = parentage1.next()
                if pointer1:
                    line1.append(pointer1)
            if pointer2:
                for item1 in line1:
                    if pointer2.id == item1.id:
                        return pointer2
                pointer2 = parentage2.next()
                if pointer2:
                    line2.append(pointer2)
        return None


class Parentage(ChangeArithmetic):

    def __init__(self, changeset):
        self.changeset = changeset
        self.register = AbstractChangesetRegister()

    def next(self):
        self.changeset = self.get_parent(self.changeset)
        return self.changeset

    def get_parent(self, changeset):
        if not changeset.follows_id:
            return None
        return self.register.get(changeset.follows_id)


class Heads(object):  # Rework as a list.

    def ids(self):
        head_ids = []
        followed_ids = {}
        closed_ids = {}
        changeset_ids = []
        register = ChangesetRegister()
        changesets = register.values()
        for changeset in changesets:
            changeset_ids.append(changeset.id)
            if changeset.closes_id:
                closed_ids[changeset.closes_id] = changeset.id
            if changeset.follows_id:
                followed_ids[changeset.follows_id] = changeset.id
        for id in changeset_ids:
            if id not in followed_ids:
                head_ids.append(id)
        return head_ids

 
class Sum(ChangeArithmetic):

    def __init__(self, changes1, changes2):
        self.changes1 = changes1  # List of Change instances.
        self.changes2 = changes2  # List of Change instances.

    def is_conflicting(self):
        try:
            self.detect_conflict()
        except ConflictException:
            return True
        else:
            return False

    def detect_conflict(self):
        refs1 = {}
        refs2 = {}
        for change1 in self.changes1:
            for change2 in self.changes2:
                if change1.ref == change2.ref:
                    old1 = change1.old
                    old2 = change2.old
                    new1 = change1.new
                    new2 = change2.new
                    if old1 == None or old2 == None or new1 == None or new2 == None:
                        if old1 != None or old2 != None or new1 != None or new2 != None:
                            msg = "Changes conflict about object lifetime on ref: %s %s" % (change1, change2)
                            raise ConflictException, msg
                    elif new1 and new2:
                        for name, value in new1.items():
                            if name in new2 and value != new2[name]:
                                msg = "Changes conflict about new values of '%s' on %s: %s or %s" % (
                                    name, change1.ref, value, new2[name]
                                )
                                raise ConflictException, msg

    def get_sequence(self):
        return [self.changes1, self.changes2]

        
class Merge(object):

    def __init__(self, changeset_continuing, changeset_closing):
        self.head1 = changeset_continuing
        self.head2 = changeset_closing
        self.range_sum = None
        self.range1 = None
        self.range2 = None
        self.common_ancestor = None

    def is_conflicting(self):
        sum = self.get_range_sum()
        return sum.is_conflicting()

    def create_mergeset(self):
        head_ids = Heads().ids()
        if self.head1.id not in head_ids:
            msg = "Changeset '%s' is not a head." % self.head1.id
            raise Exception, msg
        if self.head2.id not in head_ids:
            msg = "Changeset '%s' is not a head." % self.head2.id
            raise Exception, msg
        sum = self.get_range_sum()
        sum.detect_conflict()
        register = ChangesetRegister()
        closed_branch_changes = self.range2.calc_changes()
        mergeset = register.create_entity(
            closes_id=self.head2.id,
            follows_id=self.head1.id,
            changes = closed_branch_changes
        )
        return mergeset
 
    def get_range_sum(self):
        if self.range_sum == None:
            range1 = self.get_range1()
            range2 = self.get_range2()
            changes1 = range1.calc_changes()
            changes2 = range2.calc_changes()
            self.range_sum = Sum(changes1, changes2)
        return self.range_sum

    def get_range1(self):
        if self.range1 == None:
            self.range1 = self.create_merge_range(self.head1)
        return self.range1

    def get_range2(self):
        if self.range2 == None:
            self.range2 = self.create_merge_range(self.head2)
        return self.range2

    def create_merge_range(self, head):
        range = Range(self.get_common_ancestor(), head)
        range.pop_first()  # Don't include common ancestor.
        return range

    def get_common_ancestor(self):
        if self.common_ancestor == None:
            changeset = CommonAncestor(self.head1, self.head2).find()
            self.common_ancestor = changeset
        return self.common_ancestor


class ObjectRegister(ChangesetLayerBase):
    """Abstract dictionary-like interface to changeset objects."""

    object_type = None
    key_attr = ''
    distinct_attrs = []

    def __init__(self):
        assert self.object_type, "Missing domain object type on %s" % self
        assert self.key_attr, "Missing key attribute name on %s" % self

    def __getitem__(self, key, default=Exception):
        return self.get(key, default=default)

    def get(self, key, default=Exception, attr=None):
        if attr == None:
            attr = self.key_attr
        kwds = {attr: key}
        q = Session.query(self.object_type).autoflush(False)
        #q = Session.query(self.object_type).autoflush(True)
        o = q.filter_by(**kwds).first()
        if o:
            return o
        if default != Exception:
            return default
        else:
            raise Exception, "%s not found: %s" % (self.object_type.__name__, key)

    def __len__(self):
        return len(self._all())

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, key):
        return key in self.keys()

    def _all(self):
        return Session.query(self.object_type).all()

    def items(self):
        return [(getattr(o, self.key_attr), o) for o in self._all()]

    def keys(self):
        return [getattr(o, self.key_attr) for o in self._all()]

    def values(self):
        return self._all()

    def create_entity(self, *args, **kwds):
        if args:
            kwds[self.key_attr] = args[0]
        entity = self.object_type(**kwds)
        Session.add(entity)
        return entity

    def detect_conflict(self, key, vector):
        entity = self.get(key, None)
        if entity:
            self.detect_prechange_divergence(entity, vector)
        else:
            if vector.old:
                msg = "Entity '%s' not found for changeset with old values: %s" % (key, vector.old)
                raise ConflictException, msg
            self.detect_missing_values(vector)
        self.detect_distinct_value_conflict(vector)

    def detect_prechange_divergence(self, entity, vector):
        "Checks for diverged pre-change values."
        if not vector.old:
            return
        entity_data = entity.as_dict()
        for name in vector.old.keys():
            entity_value = entity_data[name]
            old_value = vector.old[name]
            if entity_value != old_value:
                msg = u"Current entity '%s' conflicts with old value of the change." % name
                msg += "\n<<<\n%s\n<<<\n--\n>>>\n%s\n>>>" % (entity_value, old_value)
                raise ConflictException, msg.encode('utf8')

    def detect_distinct_value_conflict(self, vector):
        "Checks for unique value conflicts with existing entities."
        for name in self.distinct_attrs:
            if not name in vector.new:
                continue
            elif not self.get(vector.new[name], None, attr=name):
                continue
            else:
                msg = "Conflicting unique '%s' values: '%s'." % (
                    name, vector.new[name])
                raise ConflictException, msg

    def detect_missing_values(self, vector):
        for name in self.distinct_attrs:
            if name in vector.new and vector.new[name]:
                continue
            msg = "Missing value '%s': '%s'." % (name, vector.new)
            raise ConflictException, msg

    def ref(self, entity):
        return u'/%s/%s' % (
            self.object_type.__name__.lower(),
            getattr(entity, self.key_attr)
        )

    def diff(self, entity):
        history = entity.all_revisions
        age = len(history)
        if age == 0:
            raise Exception, "Object has no revisions: %s" % repr(entity)
        elif age == 1:
            previous = None
        elif age >= 2:
            previous = history[1]
        old_data = None  # Signifies object creation.
        new_data = entity.as_dict()
        del(new_data['revision_id'])
        if previous:
            old_data = {}
            for name in entity.revisioned_fields:
                old_value = getattr(previous, name)
                new_value = new_data[name]
                if old_value == new_value:
                    del(new_data[name])
                else:
                   old_data[name] = old_value
        return Vector(old_data, new_data)

    def patch(self, entity, vector):
        for col in self.get_columns():
            if col.name in vector.new:
                value = vector.new[col.name]
                type_name = col.type.__class__.__name__
                value = self.convert_to_domain_value(value, type_name)
                setattr(entity, col.name, value)

    def get_columns(self):
        from ckan.model.core import orm
        table = orm.class_mapper(self.object_type).mapped_table
        return table.c

    def convert_to_domain_value(self, value, type_name):
        if type_name in ['Unicode', 'UnicodeText']:
            if value == None:
                pass
            else:
                value = unicode(value)
        elif type_name in ['DateTime']:
            if value == None:
                pass
            else:
                import datetime, re
                value = datetime.datetime(*map(int, re.split('[^\d]', value)))
        else:
            raise Exception, "Unsupported type: %s" % type_name
        return value


class AbstractChangesetRegister(ObjectRegister):
    """Dictionary-like interface to changeset objects."""

    object_type = Changeset
    key_attr = 'id'
    NAMESPACE_CHANGESET = None

    def create_entity(self, *args, **kwds):
        if 'id' not in kwds:
            kwds['id'] = self.create_changeset_id(**kwds)
        preexisting = self.get(kwds['id'], None)
        if preexisting != None:
            if 'revision_id' in kwds:
                preexisting.revision_id = kwds['revision_id']
            return preexisting
        if 'meta' in kwds:
            meta = kwds['meta']
            if isinstance(meta, dict):
                kwds['meta'] = unicode(self.dumps(meta))
        return super(AbstractChangesetRegister, self).create_entity(*args, **kwds)

    def create_changeset_id(self, **kwds):
        id_profile = []
        closes_id = kwds.get('closes_id', None)
        id_profile.append({'closes_id':'closes_id'}) # Separator.
        id_profile.append(closes_id)
        follows_id = kwds.get('follows_id', None)
        id_profile.append({'follows_id':'follows_id'}) # Separator.
        id_profile.append(follows_id)
        changes = kwds.get('changes', [])
        index = {}
        for change in changes:
            index[change.ref] = change
        refs = index.keys()
        refs.sort()
        for ref in refs:
            id_profile.append({'ref':ref}) # Separator.
            change = index[ref]
            id_profile.append({'old':'old'}) # Separator.
            if change.old:
                old_keys = change.old.keys()
                old_keys.sort()
                for key in old_keys:
                    value = change.old[key]
                    id_profile.append(key)
                    id_profile.append(value)
            id_profile.append({'new':'new'}) # Separator.
            if change.new:
                new_keys = change.new.keys()
                new_keys.sort()
                for key in new_keys:
                    value = change.new[key]
                    id_profile.append(key)
                    id_profile.append(value)
        id_profile = self.dumps(id_profile)
        id_uuid = uuid.uuid5(self.NAMESPACE_CHANGESET, id_profile)
        changeset_id = unicode(id_uuid)
        return changeset_id
            
    def update(self):
        raise Exception, "Method not implemented."

    def commit(self):
        raise Exception, "Method not implemented."

    def add_unseen(self, changeset_data):
        # Todo: Validate the data (dict with id str, meta dict, and changes list).
        changeset_id = unicode(changeset_data['id'])
        if changeset_id in self:
            raise Exception, "Already have changeset with id '%s'." % changeset_id
        closes_id = changeset_data.get('closes_id', None)
        if closes_id:
            closes_id = unicode(closes_id)
        follows_id = changeset_data.get('follows_id', None)
        if follows_id:
            follows_id = unicode(follows_id)
        meta = changeset_data['meta']
        timestamp = self.convert_to_domain_value(changeset_data.get('timestamp', None), 'DateTime')
        changes = []
        changes_data = changeset_data['changes']
        change_register = ChangeRegister()
        for change_data in changes_data:
            ref = unicode(change_data['ref'])
            diff_data = change_data['diff']
            diff = unicode(self.dumps(diff_data))
            change = change_register.create_entity(ref=ref, diff=diff)
            changes.append(change)
        changeset = self.create_entity(
            id=changeset_id,
            closes_id=closes_id,
            follows_id=follows_id,
            meta=meta, 
            timestamp=timestamp,
            changes=changes,
            status=self.object_type.STATUS_QUEUED,
        )
        Session.commit()
        Session.remove()
        return changeset.id


class ChangeRegister(ObjectRegister):
    """Dictionary-like interface to change objects."""

    object_type = Change
    key_attr = 'ref'


#############################################################################
#
## Persistence model.
#

changeset_table = Table('changeset', metadata,
        # These are the "public" changeset attributes.
        Column('id', types.UnicodeText, primary_key=True),
        Column('closes_id', types.UnicodeText, nullable=True),
        Column('follows_id', types.UnicodeText, nullable=True),
        Column('meta', types.UnicodeText, nullable=True),
        Column('timestamp', DateTime, default=datetime.datetime.utcnow),
        # These are the "private" changeset attributes.
        Column('is_tip', types.Boolean, default=False),
        Column('revision_id', types.UnicodeText, ForeignKey('revision.id'), nullable=True),
        Column('status', types.UnicodeText, nullable=True),
        Column('added_here', DateTime, default=datetime.datetime.utcnow),
)

change_table = Table('change', metadata,
        Column('ref', types.UnicodeText, nullable=True),
        Column('diff', types.UnicodeText, nullable=True),
        Column('changeset_id', types.UnicodeText, ForeignKey('changeset.id')),
)

mapper(Changeset, changeset_table, properties={
    'changes':relation(Change, backref='changeset',
        cascade='all, delete', #, delete-orphan',
        ),
    },
    order_by=changeset_table.c.added_here,
)

mapper(Change, change_table, properties={
    },
    primary_key=[change_table.c.changeset_id, change_table.c.ref] 
)


#############################################################################
#
## Statements specific to the CKAN system.
#

class ChangesetRegister(AbstractChangesetRegister):

    NAMESPACE_CHANGESET = uuid.uuid5(uuid.NAMESPACE_OID, 'opendata')

    def update(self, target_id=None, report={}):
        if not len(self):
            raise EmptyChangesetRegisterException, "There are no changesets in the changeset register."
        uncommitted, head_revision = self.get_revisions_uncommitted_and_head()
        # Check there are no uncommited revisions.
        if len(uncommitted) > 0:
            raise UncommittedChangesException, "Revisions are outstanding: %s" % " ".join([r.id for r in uncommitted])
        # Get route from tip to target.
        tip = self.get_tip()
        if not tip:
            raise Exception, "None of the changesets is marked as 'tip'."
        head_ids = Heads().ids()
        if tip.id in head_ids:
            raise TipAtHeadException, "Nothing to update (tip is head of its line)."
        range = None
        if target_id:
            range = Range(tip, self.get(target_id))
            if range.is_broken():
                raise Exception, "Target is not on tip's branch."
                # Todo: Make a jump.
        else:
            # Find the head for this id.
            for head_id in head_ids:
                range = Range(tip, self.get(head_id))
                if not range.is_broken():
                    target_id = head_id
                    break
            if not target_id:
                raise Exception, "Can't work out which changeset to make tip."
        if range:
            # It's on the range so we can move forward through the revisions.
            for changeset in range.get_changesets()[1:]:
                 changeset.apply(report=report)
                 print "Applied changeset  %s" % changeset.id
            print ", ".join(["%s %s packages" % (key, len(val)) for (key, val) in report.items()])
            # Todo: Make a better report.
        # else: apply a 'jump'

#    def apply_jump_changes(self, jump):
#        # Jump to the target in one revision.
#        range.pop_first()
#        changes = range.calc_changes()
#        # Apply changes.
#        message = u'Jumped to changeset %s' % target_id
#        author = u'system'
#        revision_id, updated, created, deleted = self.apply_changes(changes, message, author)
#        target = self.get(target_id)
#        target.revision_id = revision_id
#        Session.commit()
#        # Move tip.
#        self.move_tip(target_id)
#        # Setup access control for created entities.
#        for entity in created_entities:
#            setup_default_user_roles(entity, [])
#        # Todo: Teardown access control for deleted entities?
#        return (updated, created, deleted)

    def apply_changes(self, changes, meta={}, report={}, is_forced=False):
        need_access_control = []
        if not 'created' in report:
            report['created'] = []
        if not 'updated' in report:
            report['updated'] = []
        if not 'deleted' in report:
            report['deleted'] = []
        revision_register_class = Change.registers['revision'] 
        revision_register = revision_register_class()
        revision = revision_register.create_entity()
        revision.message = unicode(meta.get('log_message', ''))
        revision.author = unicode(meta.get('author', ''))
        for change in changes:
            entity = change.apply(is_forced=is_forced)
            if not change.old and change.new:
                need_access_control.append(entity)
                report['created'].append(entity)
            elif change.old and change.new:
                report['updated'].append(entity)
            if change.old and not change.new:
                report['deleted'].append(entity)
        Session.commit()
        revision_id = revision.id
        # Setup access control for created entities.
        for entity in need_access_control:
            setup_default_user_roles(entity, [])
        return revision_id

    def commit(self):
        uncommitted, head_revision = self.get_revisions_uncommitted_and_head()
        tip = self.get_tip()
        if tip and not tip.revision_id:
            msg = "Tip changeset has no revision id." % tip.id
            raise Exception, msg
        if tip and head_revision and tip.revision_id != head_revision.id:
            msg = "Tip changeset points to revision '%s' (not head revision '%s')." % (tip.revision_id, head_revision.id)
            raise Exception, msg
        uncommitted.reverse()
        changeset_ids = []
        follows_id = tip and tip.id or None
        for revision in uncommitted:
            changeset_id = self.construct_from_revision(revision, follows_id=follows_id)
            changeset_ids.append(changeset_id)
            self.move_tip(changeset_id)
            follows_id = changeset_id
        return changeset_ids

    def merge(self, continuing_id):
        continuing = self.get(continuing_id)
        closing = self.get_tip()
        merge = Merge(continuing, closing)
        if merge.is_conflicting():
            raise ConflictException, "Merge conflict when closing '%s' into changeset '%s'." % (closing.id, continuing.id)
        mergeset = merge.create_mergeset()
        Session.commit()
        return mergeset

    def get_revisions_uncommitted_and_head(self):
        import ckan.model
        revisions =  ckan.model.repo.history()  # NB Youngest first.
        uncommitted = []
        head_revision = None
        for revision in revisions:
            changeset = self.get(revision.id, None, 'revision_id')
            if changeset == None:
                uncommitted.append(revision)
            else:
                head_revision = revision
                break # Assume contiguity of uncommitted revisions.
        return uncommitted, head_revision

    def get_tip(self):
        return self.get(True, None, 'is_tip')

    def move_tip(self, target_id):
        target = self.get(target_id)
        tip = self.get_tip()
        if tip:
            tip.is_tip = False
        target.is_tip = True
        Session.commit()

    def construct_from_revision(self, revision, follows_id=None):
        if follows_id:
            # Todo: Detect if the new changes conflict with the line (it's a system error).
            pass
        meta = unicode(self.dumps({
            'log_message': revision.message,
            'author': revision.author,
        }))
        changes = []
        for package in revision.packages:
            change = self.construct_package_change(package)
            changes.append(change)
        changeset = self.create_entity(
            follows_id=follows_id,
            meta=meta,
            changes=changes,
            status=self.object_type.STATUS_CONSTRUCTED,
            revision_id=revision.id,
        )
        Session.commit()
        Session.remove()
        return changeset.id

    def construct_package_change(self, package):
        packages = PackageRegister()
        ref = packages.ref(package)
        vector = packages.diff(package)
        diff = vector.as_diff()
        return ChangeRegister().create_entity(ref=ref, diff=diff)

    def pull_source(self, source):
        api_location = source.split('/api')[0].strip('/') + '/api'
        from ckanclient import CkanClient
        ckan_service = CkanClient(base_location=api_location)
        foreign_ids = ckan_service.changeset_register_get()
        if foreign_ids == None:
            msg = "Error pulling changes from: %s (CKAN service error: %s: %s)" % (source, ckan_service.last_url_error or "%s: %s" % (ckan_service.last_status, ckan_service.last_http_error), ckan_service.last_location)
            raise ChangesSourceException, msg
        local_ids = self.keys()
        unseen_ids = []
        for changeset_id in foreign_ids:
            if changeset_id not in local_ids:
                unseen_ids.append(changeset_id)
        unseen_changesets = []
        for unseen_id in unseen_ids:
            unseen_data = ckan_service.changeset_entity_get(unseen_id)
            changeset_id = self.add_unseen(unseen_data)
            if not changeset_id:
                msg = "Error: Couldn't add incoming changeset: %s" % unseen_id
                raise Exception, msg
            if unseen_id != changeset_id:
                msg = "Error: Changeset id mismatch: pulled '%s' but recorded '%s'." % (unseen_id, changeset_id)
                raise Exception, msg
        return unseen_ids


class PackageRegister(ObjectRegister):
    """Dictionary-like interface to package objects."""

    object_type = Package
    key_attr = 'id'
    distinct_attrs = ['name']

    def patch(self, entity, vector):
        super(PackageRegister, self).patch(entity, vector)
        if 'tags' in vector.new:
            register = TagRegister()
            entity.tags = []
            for tag_name in vector.new['tags']:
                if tag_name in register:
                    tag = register[tag_name]
                else:
                    tag = register.create_entity(name=tag_name)
                entity.tags.append(tag)
        if 'groups' in vector.new:
            register = GroupRegister()
            entity.groups = []
            for group_name in vector.new['groups']:
                if group_name in register:
                    group = register[group_name]
                else:
                    # Todo: More about groups, not as simple as tags.
                    group = register.create_entity(name=group_name)
                entity.groups.append(group)
        if 'license' in vector.new:
            entity.license_id = vector.new['license']
        if 'license_id' in vector.new:
            entity.license_id = vector.new['license_id']
        if 'extras' in vector.new:
            entity.extras = vector.new['extras']
        # Todo: Build PackageResource objects, appending to entity.resource.
        #if 'resources' in vector.new:
        #    entity.resources = vector.new['resources']

 
class RevisionRegister(ObjectRegister):
    """Dictionary-like interface to revision objects."""

    # Assume CKAN Revision class.
    object_type = Revision
    key_attr = 'id'

    def create_entity(self, *args, **kwds):
        from ckan.model import repo
        revision = repo.new_revision()
        if 'author' in kwds:
            revision.author = kwds['author']
        if 'message' in kwds:
            revision.message = kwds['message']
        return revision


class TagRegister(ObjectRegister):
    """Dictionary-like interface to tag objects."""

    # Assume CKAN Tag class.
    object_type = Tag
    key_attr = 'name'


class GroupRegister(ObjectRegister):
    """Dictionary-like interface to group objects."""

    # Assume CKAN Group class.
    object_type = Group
    key_attr = 'name'


Change.registers = {
    'package': PackageRegister,
    'revision': RevisionRegister,
}


