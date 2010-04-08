"""Subdomain model for distributed data version control.

Changeset Use Cases
===================

   Commit working model
       - generate changesets from working model.

   Update working model
       - adjust working model from registered changesets.

   Add unseen changesets
       - register changesets committed from a foreign working model.

   Merge lines of development
       - combine diverged lines of development into a new changeset.

   Interrogate changeset model
       - working
       - heads
       - diff
       - log

Highlighted Core
================

    Changeset domain object
        - has an id uniquely determined by the content of the changeset
        - may follow other changesets in lines of development
        - may close one line of development whilst following another
        - aggregates a set of changes to the working model
    
    Change domain object
        - has a reference to an entity in the working model
        - has a difference vector describing a change to such an entity

    Arithmetic function objects
        - vector (the difference of entity before and after a change)
        - range (one part of a line of development)
        - sum (the union of two non-conflicted sets of changes)
        - reverse (the negation of a set of changes)

    Other function objects
        - parentage (the chain of preceding changesets)
        - common ancestor (intersection of two lines of development)
        - resolve (sets final values of conflicted values)
        - overwrite (the union of two overlapping sets of changes)
        - merge (conflation of two diverging lines of development)

"""
from meta import *
import vdm.sqlalchemy
from ckan.model.core import DomainObject
from ckan.model import Session, Revision, Package
from ckan.model import PackageResource, Tag, Group
from ckan.model import setup_default_user_roles
from simplejson import dumps, loads
import datetime
import uuid


#############################################################################
#
## Changeset exception classes.
#

class ConflictException(Exception): pass

class SequenceException(Exception): pass

class WorkingAtHeadException(Exception): pass

class ChangesSourceException(Exception): pass

class UncommittedChangesException(Exception): pass

class EmptyChangesetRegisterException(Exception): pass


#############################################################################
#
## Changeset arithmetic classes.
#

class Sequence(object):
    """Calculates changes effected by a sequence of changes."""

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
        return []


class Json(object):
    """Dumps and loads JSON strings into Python objects."""

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


class Vector(Json):
    """Distance in "difference space"."""

    def __init__(self, old, new):
        self.old = old
        self.new = new

    def as_diff(self):
        data = {
            'old': self.old,
            'new': self.new,
        } 
        return unicode(self.dumps(data))


class Range(Sequence):
    """Continguous changesets along one line of development."""

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


class Sum(Sequence):
    """Adds together two sets of non-conflicting changes."""

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

        
class Reverse(object):
    """Simple negation of a list of changes."""

    def __init__(self, changes):
        self.changes = changes

    def calc_changes(self):
        changes = []
        for change in self.changes:
            vector = change.as_vector()
            reverse = Vector(old=vector.new, new=vector.old)
            diff = reverse.as_diff()
            ref = change.ref
            changes.append(Change(ref=ref, diff=diff))
        return changes


class CommonAncestor(object):
    """Intersection of two lines of development."""

    def __init__(self, child1, child2):
        self.child1 = child1
        self.child2 = child2

    def find(self):
        # Optimised for performance. Alternates between stepping back through
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


class Parentage(object):
    """Follows the chain of ancestors."""

    def __init__(self, changeset):
        self.changeset = changeset
        self.register = register_classes['changeset']()

    def next(self):
        self.changeset = self.get_parent(self.changeset)
        return self.changeset

    def get_parent(self, changeset):
        if not changeset.follows_id:
            return None
        return self.register.get(changeset.follows_id)


class Merge(object):
    """Creates changeset which closes the working line of development."""

    def __init__(self, continuing, closing):
        self.continuing = continuing
        self.closing = closing
        self.range_sum = None
        self.range1 = None
        self.range2 = None
        self.common_ancestor = None

    def is_conflicting(self):
        sum = self.get_range_sum()
        return sum.is_conflicting()

    def create_mergeset(self, resolve_class=None):
        head_ids = Heads().ids()
        if self.continuing.id not in head_ids:
            msg = "Changeset '%s' is not a head." % self.continuing.id
            raise Exception, msg
        if self.closing.id not in head_ids:
            msg = "Changeset '%s' is not a head." % self.closing.id
            raise Exception, msg
        sum = self.get_range_sum()
        if resolve_class == None:
            resolve_class = Resolve
        resolve = resolve_class(sum.changes1, sum.changes2)
        resolution = resolve.calc_changes()
        overwrite = Overwrite(sum.changes2, resolution)
        changes = overwrite.calc_changes()
        register = register_classes['changeset']()
        # Todo: Use values from the user doing the merge.
        log_message = 'Merged branch %s' % self.closing.id
        author = 'System'
        meta = {
            'log_message': log_message,
            'author': author,
        }
        mergeset = register.create_entity(
            meta=meta,
            closes_id=self.closing.id,
            follows_id=self.continuing.id,
            changes=changes
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
            self.range1 = self.create_merge_range(self.continuing)
        return self.range1

    def get_range2(self):
        if self.range2 == None:
            self.range2 = self.create_merge_range(self.closing)
        return self.range2

    def create_merge_range(self, stop):
        start = self.get_common_ancestor()
        range = Range(start, stop)
        # Drop the common ancestor.
        range.pop_first()  
        return range

    def get_common_ancestor(self):
        if self.common_ancestor == None:
            changeset = CommonAncestor(self.continuing, self.closing).find()
            self.common_ancestor = changeset
        return self.common_ancestor


class Resolve(object):
    """Decides between conflicting values."""

    def __init__(self, changes1, changes2):
        self.changes1 = changes1
        self.changes2 = changes2

    def calc_changes(self):
        changes3 = []  # A list of Change instances.
        for change1 in self.changes1:
            ref = change1.ref
            vector3 = None
            for change2 in self.changes2:
                if ref == change2.ref:
                    old1 = change1.old
                    new1 = change1.new
                    old2 = change2.old
                    new2 = change2.new
                    if old1 == None or old2 == None or new1 == None or new2 == None:
                        if old1 != None or old2 != None or new1 != None or new2 != None:
                            print "Changes conflict about object lifetime on ref: %s %s" % (change1, change2)

                            new = self.decide_value(new1, new2)
                            print "Using values: %s" % new
                            vector3 = Vector(new1, new)
                    elif new1 and new2:
                        old3 = None
                        new3 = None
                        for name, value1 in new1.items():
                            if name not in new2:
                                break
                            value2 = new2[name]
                            if value1 != value2:
                                print "Changes conflict about new values of '%s' on %s: %s or %s" % (
                                    name, ref, value1, value2
                                )
                                if old3 == None and new3 == None:
                                    old3 = {}
                                    new3 = {}
                                value = self.decide_value(value1, value2)
                                print "Using value: %s" % value
                                old3[name] = value1
                                new3[name] = value
                        if old3 != None and new3 != None:
                            vector3 = Vector(old3, new3)
                    break    
            if vector3:
                diff = vector3.as_diff()
                change3 = Change(ref=ref, diff=diff)
                changes3.append(change3)
        return changes3

    def decide_value(self, value1, value2):
        return value2


class CliResolve(Resolve):
    """Decides between conflicting values using command line intervention."""

    def decide_value(self, value1, value2):
        print "Conflicting values:"
        print "1:  %s" % value1
        print "2:  %s" % value2
        input = raw_input("Which value is best? [2]: ")
        if input == "1":
            value = value1
        else:
            value = value2
        return value


class Overwrite(object):
    """Imposes one set of changes on another."""

    def __init__(self, changes1, changes2):
        self.changes1 = changes1
        self.changes2 = changes2
        
    def calc_changes(self):
        changes = []
        # Copy 1.
        for change1 in self.changes1:
            ref = change1.ref
            vector = change1.as_vector()
            diff = vector.as_diff()
            change = Change(ref=ref, diff=diff)
            changes.append(change)
        # Update copy from 2.
        for change2 in self.changes2:
            is_overwrite = False
            for change in changes:
                if change2.ref == change.ref:
                    vector = change.as_vector()
                    vector2 = change2.as_vector()
                    vector.old.update(vector2.old)
                    vector.new.update(vector2.new)
                    change.diff = vector.as_diff()
                    is_overwrite = True
                    break
            if not is_overwrite:
                ref = change2.ref
                vector = change2.as_vector()
                diff = vector.as_diff()
                change = Change(ref=ref, diff=diff)
                changes.append(change)
        return changes


#############################################################################
#
## Changeset subdomain model objects and registers.
#

register_classes = {}

class ChangesetSubdomainObject(DomainObject, Json):

    pass


class Changeset(ChangesetSubdomainObject):
    """Models a set of changes made to a working model."""
   
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
        register = register_classes['changeset']()
        Session.add(self) # Otherwise self.changes db lazy-load doesn't work.
        revision_id = register.apply_changes(self.changes, 
            meta=meta, report=report, is_forced=is_forced)
        Session.add(self) # Otherwise revision_id isn't persisted.
        self.revision_id = revision_id
        self.status = self.STATUS_APPLIED
        Session.commit()
        register.move_working(self.id)
        return revision_id

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


class Change(ChangesetSubdomainObject):
    """Models a changes made to an entity in the working model."""

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
            entity.delete()
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
        if register_type in register_classes:
            register_class = register_classes[register_type]
            register = register_class()
            return (register, register_key)
        else:
            raise Exception, "Can't deref '%s' with register map: %s" % (self.ref, register_classes)

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


class ObjectRegister(object):
    """Dictionary-like domain object register base class."""

    object_type = None
    key_attr = ''

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

    def _all(self):
        return Session.query(self.object_type).all()

    def __len__(self):
        return len(self._all())

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, key):
        return key in self.keys()

    def keys(self):
        return [getattr(o, self.key_attr) for o in self._all()]

    def items(self):
        return [(getattr(o, self.key_attr), o) for o in self._all()]

    def values(self):
        return self._all()

    def create_entity(self, *args, **kwds):
        if args:
            kwds[self.key_attr] = args[0]
        entity = self.object_type(**kwds)
        Session.add(entity)
        return entity


class TrackedObjectRegister(ObjectRegister):
    """Abstract dictionary-like interface to changeset objects."""

    distinct_attrs = []

    def detect_conflict(self, key, vector):
        """Checks whether the vector conflicts with the working model."""
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
        """Checks vector old values against the current working model."""
        if not vector.old:
            return
        entity_data = entity.as_dict()
        for name in vector.old.keys():
            entity_value = entity_data[name]
            old_value = vector.old[name]
            if not self.is_equal(entity_value, old_value):
                msg = u"Current '%s' value conflicts with old value of the change.\n" % name
                msg += "current: %s\n" % entity_value
                msg += "change old: %s\n" % old_value
                raise ConflictException, msg.encode('utf8')

    def is_equal(self, value1, value2):
        """Compares domain values for equality."""
        # Todo: Should list order differences be conflicts?
        #   - why would the order (e.g. tags of a package) change?
        if isinstance(value1, list):
            value1.sort()
        if isinstance(value2, list):
            value2.sort()
        return value1 == value2

    def detect_distinct_value_conflict(self, vector):
        """Checks for unique value conflicts with existing entities."""
        for name in self.distinct_attrs:
            if vector.new == None:
                # There aren't any new values.
                continue
            elif name not in vector.new:
                # The new values don't include this attribute.
                continue
            elif not self.get(vector.new[name], None, attr=name):
                # The new values aren't already in use.
                continue
            else:
                msg = "Conflicting unique '%s' values: '%s'." % (
                    name, vector.new[name])
                raise ConflictException, msg

    def detect_missing_values(self, vector):
        """Checks for required values such as distinct values."""
        for name in self.distinct_attrs:
            if name in vector.new and vector.new[name]:
                continue
            msg = "Missing value '%s': '%s'." % (name, vector.new)
            raise ConflictException, msg

    def ref(self, entity):
        """Returns path-like string that can reference given entity."""
        return u'/%s/%s' % (
            self.object_type.__name__.lower(),
            getattr(entity, self.key_attr)
        )

    def diff(self, entity):
        """Instantiates and returns a vector for the difference
        between the current and previous versions of given entity."""
        raise Exception, "Abstract method not implemented."

    def patch(self, entity, vector):
        """Updates given entity according to the given vector of change."""
        for col in self.get_columns():
            if col.name in vector.new:
                value = vector.new[col.name]
                type_name = col.type.__class__.__name__
                value = self.convert_to_domain_value(value, type_name)
                setattr(entity, col.name, value)

    def get_columns(self):
        """Returns the model of the entity attributes."""
        from ckan.model.core import orm
        table = orm.class_mapper(self.object_type).mapped_table
        return table.c

    def convert_to_domain_value(self, value, type_name):
        """Returns a domain value for the given serialised value and type."""
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


class AbstractChangesetRegister(TrackedObjectRegister, Json):
    """Dictionary-like interface to changeset objects."""

    object_type = Changeset
    key_attr = 'id'
    NAMESPACE_CHANGESET = None

    def pull(self, source):
        """Detects and retrieves unseen changesets from given source."""
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

    def update(self, target_id=None, report={}):
        """Adjusts the working model to correspond with the target 
        changeset, which defaults to the head of the working line."""
        if not len(self):
            raise EmptyChangesetRegisterException, "There are no changesets in the changeset register."
        # Check there are no outstanding changes.
        if self.is_outstanding_changes():
            raise UncommittedChangesException, "There are outstanding changes in the working data."
        # Get route from working to target.
        working = self.get_working()
        if not working:
            raise Exception, "There is no working changeset."
        head_ids = Heads().ids()
        if not target_id:
            # Infer a target from the list of heads.
            if working.id in head_ids:
                raise WorkingAtHeadException, "Nothing to update (working changeset is head of its line)."
            else:
                for head_id in head_ids:
                    range = Range(working, self.get(head_id))
                    if not range.is_broken():
                        target_id = head_id
                        break
                if not target_id:
                    raise Exception, "Can't find head changeset for the working line."
        target = self.get(target_id)
        range_forward = None
        range_back = None
        # Infer a path from the target.
        common = CommonAncestor(working, target)
        ancestor = common.find()
        if ancestor.id == working.id:
            # Just go forward towards head.
            range_forward = Range(working, target)
        elif ancestor.id == target.id:
            # Just go back towards root.
            range_back = Range(target, working)
        else:
            # Go back and then go forward.
            range_forward = Range(ancestor, target)
            range_back = Range(ancestor, working)
        if range_forward and range_back == None:
            # It's on the range so we can move forward through the revisions.
            print "Applying changesets individually..."
            range_forward.pop_first()
            for changeset in range_forward.get_changesets()[1:]:
                 print "%s" % changeset.id
                 changeset.apply(report=report)
        elif range_back and range_forward == None:
            print "Updating to a previous point on the line..."
            range_back.pop_first()
            changes = range_back.calc_changes()
            reverse = Reverse(changes)
            changes = reverse.calc_changes()
            self.apply_jump_changes(changes, target_id, report=report)
            # Todo: Make a better report.
        elif range_back and range_forward:
            print "Crossing branches..."
            range_forward.pop_first()
            changes_forward = range_forward.calc_changes()
            range_back.pop_first()
            changes = range_back.calc_changes()
            reverse = Reverse(changes)
            changes_back = reverse.calc_changes()
            sum = Sum(changes_back, changes_forward)
            changes = sum.calc_changes()
            self.apply_jump_changes(changes, target_id, report=report)
        print ", ".join(["%s %s packages" % (key, len(val)) for (key, val) in report.items()])

    def merge(self, continuing_id, resolve_class=None):
        """Creates a new changeset combining diverged lines of development."""
        continuing = self.get(continuing_id)
        closing = self.get_working()
        merge = Merge(continuing, closing)
        mergeset = merge.create_mergeset(resolve_class=resolve_class)
        Session.commit()
        return mergeset

    def commit(self):
        """Creates a new changeset from changes made to the working model."""
        raise Exception, "Abstract method not implemented."

    def get_working(self):
        """Returns the changeset last used to update the working model."""
        return self.get(True, None, 'is_working')

    def move_working(self, target_id):
        """Switches the working changeset to the given target."""
        target = self.get(target_id)
        working = self.get_working()
        if working:
            working.is_working = False
        target.is_working = True
        Session.commit()

    def create_entity(self, *args, **kwds):
        """Instantiates a new Changeset object."""
        if 'id' not in kwds:
            kwds['id'] = self.determine_changeset_id(**kwds)
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

    def determine_changeset_id(self, **kwds):
        """Generates and returns a UUID from the changeset content."""
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
            
    def add_unseen(self, changeset_data):
        """Puts foreign changesets into the register."""
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


register_classes['changeset'] = AbstractChangesetRegister


class Heads(object):  # Rework as a list.
    """Lists changesets which have no followers."""

    def ids(self):
        head_ids = []
        followed_ids = {}
        closed_ids = {}
        changeset_ids = []
        register = register_classes['changeset']()
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

 
class ChangeRegister(TrackedObjectRegister):
    """Dictionary-like interface to change objects."""

    object_type = Change
    key_attr = 'ref'


#############################################################################
#
## Persistence model.
#

changeset_table = Table('changeset', metadata,
        ## These are the "public" changeset attributes.
        # 'id' - deterministic function of its content
        Column('id', types.UnicodeText, primary_key=True),
        # 'closes_id' - used by a mergesets to refer to its closed line
        Column('closes_id', types.UnicodeText, nullable=True),
        # 'follows_id' - refers to immediate ancestor of the changeset
        Column('follows_id', types.UnicodeText, nullable=True),
        # 'meta' - a JSON dict, optionally with author, log_message, etc.
        Column('meta', types.UnicodeText, nullable=True),
        # 'branch' - explicit name for a working line
        Column('branch', types.UnicodeText, nullable=True),
        # 'timestamp' - UTC time when changeset was constructed
        Column('timestamp', DateTime, default=datetime.datetime.utcnow),
        ## These are the "private" changeset attributes.
        # 'is_working' - true if used for last update of working data
        Column('is_working', types.Boolean, default=False),
        # 'revision_id' - refers to constructing or applied revision
        Column('revision_id', types.UnicodeText, ForeignKey('revision.id'), nullable=True),
        # 'status' - tracks local usage of changeset
        Column('status', types.UnicodeText, nullable=True),
        # 'added_here' - UTC time when chaneset was added to local register
        Column('added_here', DateTime, default=datetime.datetime.utcnow),
)

change_table = Table('change', metadata,
        # 'ref' - type and unique identifier for tracked domain entity
        Column('ref', types.UnicodeText, nullable=True),
        # 'diff' - a JSON dict containing the change vector
        Column('diff', types.UnicodeText, nullable=True),
        # 'changeset_id' - changes are aggregated by changesets
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

    def apply_jump_changes(self, changes, target_id, report={}):
        """Applies changes to CKAN repository as a 'system jump' revision."""
        log_message = u'Jumped to changeset %s' % target_id
        author = u'system'
        meta = {
            'log_message': log_message,
            'author': author,
        }
        revision_id = self.apply_changes(changes, meta=meta, report=report)
        target = self.get(target_id)
        target.revision_id = revision_id
        Session.commit()
        self.move_working(target_id)

    def apply_changes(self, changes, meta={}, report={}, is_forced=False):
        """Applies changes to CKAN repository as a single revision."""
        need_access_control = []
        if not 'created' in report:
            report['created'] = []
        if not 'updated' in report:
            report['updated'] = []
        if not 'deleted' in report:
            report['deleted'] = []
        revision_register_class = register_classes['revision'] 
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
        # Todo: On error, rollback and reraise.
        Session.commit()
        revision_id = revision.id
        # Setup access control for created entities.
        for entity in need_access_control:
            setup_default_user_roles(entity, [])
        # Todo: Teardown access control for deleted entities?
        return revision_id

    def commit(self):
        """Constructs changesets from uncommitted CKAN repository revisions."""
        uncommitted, head_revision = self.get_revisions_uncommitted_and_head()
        working = self.get_working()
        if working and not working.revision_id:
            msg = "Working changeset '%s' has no revision id." % working.id
            raise Exception, msg
        if working and head_revision and working.revision_id != head_revision.id:
            msg = "Working changeset points to revision '%s' (not head revision '%s')." % (working.revision_id, head_revision.id)
            raise Exception, msg
        uncommitted.reverse()
        changeset_ids = []
        follows_id = working and working.id or None
        for revision in uncommitted:
            changeset_id = self.construct_from_revision(revision, follows_id=follows_id)
            changeset_ids.append(changeset_id)
            self.move_working(changeset_id)
            follows_id = changeset_id
        return changeset_ids

    def construct_from_revision(self, revision, follows_id=None):
        """Finds uncommitted CKAN repository revisions."""
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
        """Makes a changeset Change object from a CKAN package instance."""
        packages = PackageRegister()
        ref = packages.ref(package)
        vector = packages.diff(package)
        diff = vector.as_diff()
        return ChangeRegister().create_entity(ref=ref, diff=diff)

    def is_outstanding_changes(self):
        """Checks for uncommitted revisions in CKAN repository."""
        uncommitted, head_revision = self.get_revisions_uncommitted_and_head()
        return len(uncommitted) > 0

    def get_revisions_uncommitted_and_head(self):
        """Finds uncommitted revisions in CKAN repository."""
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
                # Assume contiguity of uncommitted revisions.
                break 
        return uncommitted, head_revision


class PackageRegister(TrackedObjectRegister):
    """Dictionary-like interface to package objects."""

    object_type = Package
    key_attr = 'id'
    distinct_attrs = ['name']

    def diff(self, entity):
        """Instantiates and returns a Vector for the difference
        between the current and previous Package version."""
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
        """Updates Package according to the vector of change."""
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
        if 'resources' in vector.new:
            for resource_data in vector.new['resources']:
                package_resource = PackageResource(
                    url=resource_data.get('url', u''),
                    format=resource_data.get('format', u''),
                    description=resource_data.get('description', u''),
                    hash=resource_data.get('hash', u''),
                )
                Session.add(package_resource)
                entity.resources.append(package_resource) 

 
class RevisionRegister(ObjectRegister):
    """Dictionary-like interface to revision objects."""

    # Assume CKAN Revision class.
    object_type = Revision
    key_attr = 'id'

    def create_entity(self, *args, **kwds):
        """Creates new Revision instance with author and message."""
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


register_classes['changeset'] = ChangesetRegister
register_classes['revision'] = RevisionRegister
register_classes['package'] = PackageRegister

