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
        - may 'follow' other changesets in lines of development
        - may 'close' one changeset whilst following another
        - aggregates a list of changes to the working model
    
    Change domain object
        - has a reference to an entity in the working model
        - has a difference vector describing a change to such an entity

    Change calculations:
        - vector (the difference to an entity that is effected by a change)
        - sequence (the effective set of changes for a list of sets of changes)
        - intersection (the last common changeset of any two lines)
        - sum (the effective list of changes for two non-conflicting sets of changes)
        - reverse (the effective negation for a list of changes)
        - range (the effective list of changes for part of a line)
        - line (a contiguous series of changesets)
        - reduce (deflates a list of changes in respect of any invariance)
        - realign (adjusts one list of changes to follow another)
        - resolve (decides conflicted values in diverging lines)
        - merge (conflation of two potentially conflicting lines)


    Other function objects

"""
from meta import *
from vdm.sqlalchemy import StatefulObjectMixin
from ckan.model.core import DomainObject, State
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

class ChangesetException(Exception): pass

class ConflictException(ChangesetException): pass

class SequenceException(ChangesetException): pass

class WorkingAtHeadException(ChangesetException): pass

class ChangesSourceException(ChangesetException): pass

class UncommittedChangesException(ChangesetException): pass

class EmptyChangesetRegisterException(ChangesetException): pass

class NoIntersectionException(ChangesetException): pass


#############################################################################
#
## Changeset arithmetic classes.
#

class Merge(object):
    """Creates changeset which closes one line and continues another."""

    def __init__(self, closing, continuing):
        self.closing = closing
        self.continuing = continuing
        self.range_sum = None
        self.range1 = None
        self.range2 = None
        self.intersection = None

    def is_conflicting(self):
        sum = self.get_range_sum()
        return sum.is_conflicting()

    def create_mergeset(self, resolve_class=None):
        # Identify closing and continuing changes.
        sum = self.get_range_sum()
        closing = sum.changes1
        continuing = sum.changes2
        # Resolve conflicts between diverging changes.
        if resolve_class == None:
            resolve_class = Resolve
        resolve = resolve_class(closing, continuing)
        resolving = resolve.calc_changes()
        # Sum the closing and resolution changes to make the merging changes.
        merging = Sum(closing, resolving).calc_changes()
        # Realign merging's old values to avoid conflict with continuing's new values.
        merging = Realign(continuing, merging).calc_changes()
        # Reduce the merging changes.
        merging = Reduce(merging).calc_changes()
        # Assert there are no conflicts with continuing line.
        try:
            Sum(continuing, merging).detect_conflict()
        except ConflictException, inst:
            msg = "Merge in a non-sequitur for the continuing line: %s" % inst
            raise ConflictException, msg
        # Create a new changeset with these changes.
        # Todo: Use message and author provided by the user doing the merge.
        log_message = 'Merged changes from %s to %s.' % (
            self.intersection.id, self.closing.id
        )
        author = 'system'
        meta = {
            'log_message': log_message,
            'author': author,
        }
        register = register_classes['changeset']()
        changeset = register.create_entity(
            meta=meta,
            closes_id=self.closing.id,
            follows_id=self.continuing.id,
            changes=merging
        )
        return changeset
 
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
            self.range1 = self.create_merge_range(self.closing)
        return self.range1

    def get_range2(self):
        if self.range2 == None:
            self.range2 = self.create_merge_range(self.continuing)
        return self.range2

    def create_merge_range(self, stop):
        start = self.get_intersection()
        range = Range(start, stop)
        # Drop the common ancestor.
        range.pop_first()  
        return range

    def get_intersection(self):
        if self.intersection == None:
            changeset = Intersection(self.continuing, self.closing).find()
            self.intersection = changeset
        return self.intersection


class Resolve(object):
    """Identifies and decides between conflicting changes."""

    def __init__(self, changes1, changes2):
        self.changes1 = changes1
        self.changes2 = changes2

    def calc_changes(self):
        resolution = []
        resolution_uniqueness_violations = []
        resolution_value_conflicts = []
        # Todo: Push this data down to CKAN statements (somehow).
        unique_aspects = ['/package@name']
        # NB No need to check for violations with the total model: if branch1
        # doesn't lead to violation, and branch2 doesn't lead to violation,
        # and branch2 changes don't violate uniqueness in branch1, then merge
        # shouldn't lead to violation. So there's no need to check further back
        # than the common ancestor.
        # Resolve any duplication of unique attribute values.
        #  - e.g. names of packages must be unique
        for aspect in unique_aspects:
            unique_values = {}
            ref, attr_name = aspect.split('@')
            for change in self.changes2 + self.changes1:
                if not change.ref.startswith(ref):
                    continue
                if change.new == None:
                    continue
                if attr_name not in change.new:
                    continue
                change_value = change.new[attr_name]
                if change_value not in unique_values:
                    # No other uses of this unique value detected so far.
                    unique_values[change_value] = change.ref
                elif unique_values[change_value] == change.ref:
                    # It's the same value, but on the same entity.
                    continue
                else:
                    # It's the same value, but on a different entity.
                    msg = "Changes violate unique '%s' value constraint ('%s' used on both %s and %s)." % (
                        attr_name, change_value, unique_values[change_value], change.ref
                    )
                    print msg
                    entity_id = change.ref.split('/')[2]
                    mangled_value = change_value + '-' + entity_id
                    try:
                        # Prefer the mangled value over the duplicate value.
                        decided_value = self.decide_value(mangled_value, change_value)
                    except ConflictException:
                        msg = "Unable to resolve duplicate "
                        msg += "%s '%s' " % (attr_name, change_value)
                        duplicating_ref = unique_values[change_value] 
                        msg += "(on %s and %s)." % (change.ref, duplicating_ref)
                        raise ConflictException, msg
                    if decided_value == change_value:
                        raise ConflictException, msg
                    print "Using value: %s" % decided_value
                    vector = change.as_vector()
                    vector.new[attr_name] = decided_value
                    # Update the change directly, so if it is involved in any
                    # value resolutions the new name will be carried forward.
                    change.set_diff(vector.as_diff())
                    resolution_uniqueness_violations.append(change)
        # Resolve any conflicting entity attribute values.
        for change1 in self.changes1:
            ref = change1.ref
            vector3 = None
            for change2 in self.changes2:
                vector1 = change1.as_vector()
                vector2 = change2.as_vector()
                old1 = vector1.old
                old2 = vector2.old
                new1 = vector1.new
                new2 = vector2.new
                if ref == change2.ref:
                    if (new1 == None and new2 != None) or (new1 != None and new2 == None):
                        print "Changes conflict about object lifetime: %s %s" % (change1, change2)
                        # Prefer the continuing value over the closing value.
                        new = self.decide_value(new2, new1)
                        print "Using values: %s" % new
                        vector3 = Vector(new1, new)
                    elif new1 and new2:
                        old3 = None
                        new3 = None
                        for name, value1 in new1.items():
                            if name not in new2:
                                break
                            value2 = new2[name]
                            if not vector1.is_equal(value1, value2):
                                print "Changes conflict about new values of '%s' on %s: %s or %s" % (
                                    name, ref, value1, value2
                                )
                                if old3 == None and new3 == None:
                                    old3 = {}
                                    new3 = {}
                                # Prefer the continuing value over the closing value.
                                value3 = self.decide_value(value2, value1)
                                print "Using value: %s" % value3
                                old3[name] = value1
                                new3[name] = value3
                        if old3 != None and new3 != None:
                            vector3 = Vector(old3, new3)
                    break    
            if vector3:
                diff = vector3.as_diff()
                change3 = Change(ref=ref, diff=diff)
                resolution_value_conflicts.append(change3)
        changes3 = resolution_value_conflicts
        for change in resolution_uniqueness_violations:
            # Append any changes resolved only for uniqueness.
            if change.ref not in [c.ref for c in changes3]:
                changes3.append(change)
        # NB Don't ever reduce here, because resolution changes are imposed on
        # the closing range changes within a merge, so all values need carrying.
        return changes3

    def decide_value(self, preferred, alternative):
        raise ConflictException, "Unable to resolve conflicted values '%s' and '%s'." % (preferred, alternative)


class AutoResolve(Resolve):

    def decide_value(self, preferred, alternative):
        print "Auto-resolving conflicting values:"
        print "1:  %s  <--- auto-selected" % preferred.encode('utf8')
        print "2:  %s" % alternative.encode('utf8')
        return preferred


class AutoResolvePreferClosing(Resolve):

    def decide_value(self, preferred, alternative):
        print "Auto-resolving conflicting values:"
        print "1:  %s" % preferred.encode('utf8')
        print "2:  %s  <--- auto-selected" % alternative.encode('utf8')
        return alternative


class CliResolve(Resolve):
    """Decides between conflicting values using command line intervention."""

    def decide_value(self, preferred, alternative):
        print "Please decide between these values:"
        print "1:  %s" % preferred
        print "2:  %s" % alternative
        input = raw_input("Which value do you prefer? [1]: ")
        if input == "2":
            value = alternative
        else:
            value = preferred
        return value


class Realign(object):
    """Adjust changes2 to follow changes1 without conflict."""

    def __init__(self, changes1, changes2):
        self.changes1 = changes1
        self.changes2 = changes2

    def calc_changes(self):
        "Uses changes1's new values for changes2's old values."
        for change2 in self.changes2:
            ref = change2.ref
            for change1 in self.changes1:
                if change1.ref == ref:
                    vector2 = change2.as_vector()
                    vector1 = change1.as_vector()
                    is_changed = False
                    if vector2.old == None and vector1.new == None:
                        pass
                    elif vector2.old != None and vector1.new != None:
                        for attr_name in vector2.new:
                            if attr_name in vector1.old:
                                intermediate_value = vector1.new[attr_name]
                                vector2.old[attr_name] = intermediate_value
                                is_changed = True
                    else:
                        vector2.old = vector1.new
                        is_changed = True
                    if is_changed:
                        change2.set_diff(vector2.as_diff())
        return self.changes2


class Reduce(object):
    """Reduce changes by eliminating any invariance."""

    def __init__(self, changes):
        self.changes = changes

    def calc_changes(self):
        reduction = []
        for change in self.changes:
            vector = change.as_vector()
            # Reduce any invariant non-entities.
            if vector.old == None and vector.new == None:
                continue
            # Reduce any invariant attribute values.
            if vector.old and vector.new:
                for attr_name,value_old in vector.old.items():
                    if attr_name in vector.new:
                        value_new = vector.new[attr_name]
                        if vector.is_equal(value_old, value_new):
                            del vector.old[attr_name]
                            del vector.new[attr_name]
            # Reduce any invariant entities.
            if vector.old == {} and vector.new == {}:
                continue
            change.set_diff(vector.as_diff())
            reduction.append(change)
        return reduction


class Line(object):
    """Iterator steps back up the line towards its origin."""

    def __init__(self, changeset):
        self.changeset = changeset
        self.register = register_classes['changeset']()

    def next(self):
        if self.changeset:
            if self.changeset.follows_id:
                self.changeset = self.register.get(self.changeset.follows_id)
            else:
                self.changeset = None
        else:
            raise Exception, "Can't go beyond the origin."
        return self.changeset


class Range(object):
    """Continguous changesets along one line of development."""

    def __init__(self, start, stop):
        self.start = start
        self.stop = stop
        self.sequence = None
        self.changesets = None

    def is_broken(self):
        try:
            self.get_changesets()
        except SequenceException:
            return True
        else:
            return False

    def calc_changes(self):
        return self.get_sequence().calc_changes()

    def pop_first(self):
        return self.get_sequence().pop_first()

    def get_sequence(self):
        if self.sequence == None:
            self.sequence = Sequence([])
            for changeset in self.get_changesets():
                self.sequence.append(changeset.changes)
        return self.sequence

    def get_changesets(self):
        if self.changesets == None:
            line = Line(self.stop)
            self.changesets = [self.stop]
            changeset = self.stop
            while(changeset.id != self.start.id):
                changeset = line.next()
                if changeset == None:
                    msg = "Changeset %s does not follow changeset %s." % (self.stop.id, self.start.id)
                    raise SequenceException, msg
                self.changesets.append(changeset)
            self.changesets.reverse()
        return self.changesets


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


class Sum(object):
    """Concatentations of two sets of changes."""

    def __init__(self, changes1, changes2):
        self.changes1 = changes1
        self.changes2 = changes2

    def is_conflicting(self):
        try:
            self.detect_conflict()
        except ConflictException:
            return True
        else:
            return False

    def detect_conflict(self):
        """Raises exception if a non-sequitur is detected."""
        refs1 = {}
        refs2 = {}
        for change1 in self.changes1:
            for change2 in self.changes2:
                if change1.ref == change2.ref:
                    vector1 = change1.as_vector()
                    vector2 = change2.as_vector()
                    old1 = vector1.old
                    old2 = vector2.old
                    new1 = vector1.new
                    new2 = vector2.new
                    if (new1 == None and old2 != None) or (new1 != None and old2 == None):
                        msg = "Changes conflict about object lifetime on ref "
                        msg += " '%s' when summing  %s  and  %s." % (change1.ref, change1, change2)
                        raise ConflictException, msg
                    elif new1 and old2:
                        for name, value1 in new1.items():
                            if name not in old2:
                                continue
                            value2 = old2[name]
                            if not vector1.is_equal(value1, value2):
                                msg = "Changes conflict about intermediate value of '%s' on %s: %s or %s" % (
                                    name, change1.ref, value1, value2
                                )
                                raise ConflictException, msg

    def calc_changes(self):
        return Sequence([self.changes1, self.changes2]).calc_changes()

        
class Intersection(object):
    """Intersection of two lines of development."""

    def __init__(self, child1, child2):
        self.child1 = child1
        self.child2 = child2

    def find(self):
        # Alternates between stepping back through one line searching
        # for each changeset in other line's stack and vice versa.
        # Intersection is the first changeset discovered in both lines.
        line1 = Line(self.child1)
        line2 = Line(self.child2)
        stack1 = [self.child1]
        stack2 = [self.child2]
        pointer1 = self.child1
        pointer2 = self.child2
        while (pointer1 or pointer2):
            if pointer1:
                for item2 in stack2:
                    if pointer1.id == item2.id:
                        return pointer1
                pointer1 = line1.next()
                if pointer1:
                    stack1.append(pointer1)
            if pointer2:
                for item1 in stack1:
                    if pointer2.id == item1.id:
                        return pointer2
                pointer2 = line2.next()
                if pointer2:
                    stack2.append(pointer2)
        return None


class Sequence(object):
    """A list of lists of changes."""

    def __init__(self, changeses):
        self.changeses = changeses 

    def calc_changes(self):
        cache = {}
        for changes in self.changeses:
            for change in changes:
                if change.ref not in cache:
                    cache[change.ref] = Vector(change.old, change.new)
                vector = cache[change.ref]
                # Oldest old value...
                if vector.old != None and change.old != None:
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

    def pop_first(self):
        return self.changeses.pop(0)

    def append(self, changes):
        return self.changeses.append(changes)


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

    def __init__(self, old=None, new=None):
        """Initialises instance with old and new dicts of attribute values."""
        self.old = old
        self.new = new

    def as_diff(self):
        """Converts vector data to JSON string."""
        data = {
            'old': self.old,
            'new': self.new,
        } 
        return unicode(self.dumps(data))

    def is_equal(self, value1, value2):
        """Compares vector values for equality."""
        # Todo: Should list order differences be conflicts?
        #   - why would the order (e.g. tags of a package) change?
        if isinstance(value1, list):
            value1.sort()
        if isinstance(value2, list):
            value2.sort()
        if isinstance(value1, dict):
            value1 = value1.items()
            value1.sort()
        if isinstance(value2, dict):
            value2 = value2.items()
            value2.sort()
        return value1 == value2



#############################################################################
#
## Changeset subdomain model objects and registers.
#

register_classes = {}

class ChangesetSubdomainObject(DomainObject, Json):

    pass


class Changeset(ChangesetSubdomainObject):
    """Models a list of changes made to a working model."""
   
    def get_meta(self):
        return self.loads(self.meta or "{}")

    def set_meta(self, meta_data):
        self.meta = unicode(self.dumps(meta_data))

    def apply(self, is_forced=False, report={}, moderator=None):
        """Applies changeset to the working model as a single revision."""
        meta = self.get_meta()
        register = register_classes['changeset']()
        Session.add(self) # Otherwise self.changes db lazy-load doesn't work.
        changes = self.changes
        revision_id = register.apply_changes(
            changes=changes,
            meta=meta,
            report=report,
            is_forced=is_forced,
            moderator=moderator,
        )
        Session.add(self) # Otherwise revision_id isn't persisted.
        self.revision_id = revision_id
        Session.commit()
        register.move_working(self.id)
        return revision_id

    def is_conflicting(self):
        """Returns boolean value, true if model conflicts are detected."""
        try:
            self.detect_conflict()
        except ConflictException:
            return True
        else:
            return False

    def detect_conflict(self):
        """Checks changes for conflicts with the working model."""
        for change in self.changes:
            change.detect_conflict()

    def as_dict(self):
        """Presents domain data with basic data types."""
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
    """Models a change made to an entity in the working model."""

    def get_mask_register(self):
        return ChangemaskRegister()

    def get_mask(self):
        mask_register = self.get_mask_register()
        return mask_register.get(self.ref, None)

    def is_masked(self):
        return bool(self.get_mask())

    def apply(self, is_forced=False, moderator=None):
        """Operates the change vector on the referenced model entity."""
        if self.is_masked():
            print "Warning: Screening change to '%s' (mask set for ref)." % self.ref
            return
        if not is_forced:
            if moderator and not moderator.moderate_change_apply(self):
                return
            self.detect_conflict()
        mask = self.get_mask()
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
            # Mangle distinct values.
            # Todo: Move this to the package register?
            entity.name += str(uuid.uuid4())
            entity.delete()
            #entity.purge()
        else:
            # Update.
            if entity == None:
                msg = "Can't apply updating change, since entity not found for ref: %s" % self.ref
                raise Exception, msg
            entity = register.get(key)
            register.patch(entity, vector)
        return entity # keep in scope?

    def detect_conflict(self):
        """Checks for conflicts with the working model."""
        register, key = self.deref()
        register.detect_conflict(key, self.as_vector())

    def deref(self):
        """Returns the register and register key affected by the change."""
        parts = self.ref.split('/')
        register_type = parts[1]
        register_key = parts[2]
        if register_type in register_classes:
            register_class = register_classes[register_type]
            register = register_class()
            return (register, register_key)
        else:
            raise Exception, "Can't deref '%s' with register map: %s" % (self.ref, register_classes)

    def as_vector(self):
        """Returns the pure vector of change, without any reference to an entity."""
        if not hasattr(self, 'vector') or self.vector == None:
            data = self.load_diff()
            self.vector = Vector(data['old'], data['new'])
        return self.vector

    def load_diff(self):
        """Parses the stored JSON diff string into Vector data."""
        return self.loads(self.diff)

    def set_diff(self, diff):
        self.diff = diff
        self.vector = None

    def as_dict(self):
        """Presents domain data with basic data types."""
        change_data = {}
        change_data['ref'] = self.ref
        change_data['diff'] = self.load_diff()
        return change_data

    def get_old(self):
        """Method implements Vector interface, for convenience."""
        return self.as_vector().old

    old = property(get_old)

    def get_new(self):
        """Method implements Vector interface, for convenience."""
        return self.as_vector().new

    new = property(get_new)


class Changemask(ChangesetSubdomainObject):
    """Screen working model from changes to the referenced entity"""

    pass


class ObjectRegister(object):
    """Dictionary-like domain object register base class."""

    object_type = None
    key_attr = ''

    def __init__(self):
        assert self.object_type, "Missing domain object type on %s" % self
        assert self.key_attr, "Missing key attribute name on %s" % self

    def __getitem__(self, key, default=Exception):
        return self.get(key, default=default)

    def get(self, key, default=Exception, attr=None, state=State.ACTIVE):
        """Finds a single entity in the register."""
        # Todo: Implement a simple entity cache.
        if attr == None:
            attr = self.key_attr
        kwds = {attr: key}
        if issubclass(self.object_type, StatefulObjectMixin):
            if attr == 'state':
                msg = "Can't use 'state' attribute to key"
                msg += " a stateful object register."
                raise Exception, msg
            kwds['state'] = state
        q = Session.query(self.object_type).autoflush(False)
        o = q.filter_by(**kwds).first()
        if o:
            return o
        if default != Exception:
            return default
        else:
            raise Exception, "%s not found: %s" % (self.object_type.__name__, key)

    def _all(self):
        """Finds all the entities in the register."""
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
        """Registers a new entity in the register."""
        if args:
            kwds[self.key_attr] = args[0]
        if 'id' in kwds:
            deleted_entity = self.get(kwds['id'], None,
                attr='id', state=State.DELETED
            )
            if deleted_entity:
                deleted_entity.state = State.ACTIVE
                #Session.add(deleted_entity)
                return deleted_entity
        entity = self.object_type(**kwds)
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
            if not vector.is_equal(entity_value, old_value):
                msg = u"Current '%s' value conflicts with old value of the change.\n" % name
                msg += "current: %s\n" % entity_value
                msg += "change old: %s\n" % old_value
                raise ConflictException, msg.encode('utf8')

    def detect_distinct_value_conflict(self, vector):
        """Checks for unique value conflicts with existing entities."""
        if vector.new == None:
            # There aren't any new values.
            return
        for name in self.distinct_attrs:
            if name not in vector.new:
                # Not mentioned.
                continue
            existing_entity = self.get(vector.new[name], None, attr=name)
            if existing_entity == None:
                # Not already in use.
                continue
            msg = "Model already has an entity with '%s' equal to '%s': %s" % (
                name, vector.new[name], existing_entity
            )
            raise ConflictException, msg.encode('utf8')

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
                    if isinstance(value, dict):
                        value = value.items()
                        value.sort()
                    elif isinstance(value, list):
                        value.sort()
                    id_profile.append(key)
                    id_profile.append(value)
        id_profile = self.dumps(id_profile)
        id_uuid = uuid.uuid5(self.NAMESPACE_CHANGESET, id_profile)
        changeset_id = unicode(id_uuid)
        return changeset_id
            
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

    def update(self, target_id=None, report={}, moderator=None):
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
        head_ids.reverse()
        if not target_id:
            # Infer a target from the list of heads.
            # Todo: Infer cross-branch target when working changeset is closed by a mergeset.
            if working.id in head_ids:
                raise WorkingAtHeadException, "Nothing to update (working changeset is at the head of its line)."
            else:
                for head_id in head_ids:
                    range = Range(working, self.get(head_id))
                    if not range.is_broken():
                        target_id = head_id
                        break
                if not target_id:
                    raise Exception, "Can't find head changeset for the working line."
        target = self.get(target_id)
        route = Route(working, target)
        range_back, range_forward = route.get_ranges()
        if range_back == None and range_forward:
            # Step through changesets to replicate history.
            changesets = range_forward.get_changesets()[1:]
            changesets_len = len(changesets)
            print "There %s %s changeset%s..." % (
                changesets_len != 1 and "are" or "is",
                changesets_len, 
                changesets_len != 1 and "s" or ""
            )
            range_forward.pop_first()
            for changeset in range_forward.get_changesets()[1:]:
                if moderator and moderator.moderate_changeset_apply(changeset):
                    changeset.apply(report=report, moderator=moderator)
                    print "Applied changeset '%s' OK." % changeset.id
                    print ""
                elif moderator:
                    print "Not applying changeset '%s'. Stopping..." % changeset.id
                    break
                else:
                    print "%s" % changeset.id
                    changeset.apply(report=report)
        elif range_back and range_forward == None:
            print "Updating to a previous point on the line..."
            range_back.pop_first()
            changes = range_back.calc_changes()
            reverse = Reverse(changes)
            changes = reverse.calc_changes()
            changes = Reduce(changes).calc_changes()
            self.apply_jump_changes(changes, target_id, report=report, moderator=moderator)
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
            changes = Reduce(changes).calc_changes()
            self.apply_jump_changes(changes, target_id, report=report, moderator=moderator)

    def merge(self, closing_id, continuing_id, resolve_class=None):
        """Creates a new changeset combining diverged lines of development."""
        closing = self.get(closing_id)
        continuing = self.get(continuing_id)
        merge = Merge(closing=closing, continuing=continuing)
        mergeset = merge.create_mergeset(resolve_class=resolve_class)
        Session.add(mergeset)
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
        # Create changes before changeset (changeset id depends on changes).
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
        )
        Session.add(changeset)
        Session.commit()
        return changeset.id


class Route(object):

    def __init__(self, start, stop):
        self.start = start
        self.stop = stop
        self.back = None
        self.forward = None
        self.changes = None

    def get_ranges(self):
        if self.back == None and self.forward == None:
            common = Intersection(self.start, self.stop)
            ancestor = common.find()
            if ancestor == None:
                msg = "%s %s" % (self.start.id, self.stop.id)
                raise NoIntersectionException, msg
            if ancestor.id == self.start.id:
                # Just go forward towards head.
                self.forward = Range(self.start, self.stop)
            elif ancestor.id == self.stop.id:
                # Just go back towards root.
                self.back = Range(self.stop, self.start)
            else:
                # Go back and then go forward.
                self.back = Range(ancestor, self.start)
                self.forward = Range(ancestor, self.stop)
        return self.back, self.forward

    def calc_changes(self):
        if self.changes == None:
            self.get_ranges()
            changes_back = None
            changes_forward = None
            if self.back != None:
                self.back.pop_first()
                changes = self.back.calc_changes()
                changes_back = Reverse(changes).calc_changes()
            if self.forward != None:
                self.forward.pop_first()
                changes = self.forward.calc_changes()
                changes_forward = changes
            if changes_back != None and changes_forward != None:
                self.changes = Sum(changes_back, changes_forward).calc_changes()
            elif changes_back != None:
                self.changes = changes_back
            elif changes_forward != None:
                self.changes = changes_forward
        return self.changes


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

# Todo: Extract (and put under test) the mask-setting and mask-getting routines.
# Todo: Prevent user from easily not applying change and not applying mask.
# Todo: Support mask-unsetting (necessarily with entity "catch up").
# Todo: Support apply-conflict override (so some changes can be skipped).
class ChangemaskRegister(TrackedObjectRegister):
    """Dictionary-like interface to ignore objects."""

    object_type = Changemask
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
        Column('branch', types.UnicodeText, default=u'default', nullable=True),
        # 'timestamp' - UTC time when changeset was constructed
        Column('timestamp', DateTime, default=datetime.datetime.utcnow),
        ## These are the "private" changeset attributes.
        # 'is_working' - true if used for last update of working data
        Column('is_working', types.Boolean, default=False),
        # 'revision_id' - refers to constructing or applied revision
        Column('revision_id', types.UnicodeText, ForeignKey('revision.id'), nullable=True),
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

changemask_table = Table('changemask', metadata,
        # 'ref' - type and unique identifier for masked domain entity
        Column('ref', types.UnicodeText, primary_key=True),
        # 'timestamp' - UTC time when mask was set
        Column('timestamp', DateTime, default=datetime.datetime.utcnow),
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

mapper(Changemask, changemask_table, properties={
    },
    primary_key=[changemask_table.c.ref], 
    order_by=changemask_table.c.timestamp,
)


#############################################################################
#
## Statements specific to the CKAN system.
#

# Todo: Robustness against buried revisions. Figure out what would happen if auto-commit running whilst moderated update is running? Might try to apply a changeset to a newly diverged working model. Argument in favour of not running automatic commits. :-) But also if a new revision is created from the Web interface, it won't be committed but its changes will never be committed if it is followed by revision created by applying changes during an update, and so we need to check for outstanding revisions before each 'apply_changes' (not just each 'update' because the duration of time needed for moderation or to apply a long series of changesets offers the possibility for burying a lost revision). Locking the model might help, but would need to be worked into all the forms. So basically the error would be trying to apply 'next' changeset to working model that has already changed.

class ChangesetRegister(AbstractChangesetRegister):

    NAMESPACE_CHANGESET = uuid.uuid5(uuid.NAMESPACE_OID, 'opendata')

    def apply_jump_changes(self, changes, target_id, report={}, moderator=None):
        """Applies changes to CKAN repository as a 'system jump' revision."""
        log_message = u'Jumped to changeset %s' % target_id
        author = u'system'
        meta = {
            'log_message': log_message,
            'author': author,
        }
        revision_id = self.apply_changes(changes, meta=meta, report=report, moderator=moderator)
        target = self.get(target_id)
        target.revision_id = revision_id
        Session.commit()
        self.move_working(target_id)

    def apply_changes(self, changes, meta={}, report={}, is_forced=False, moderator=None):
        """Applies given changes to CKAN repository as a single revision."""
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
        # Apply deleting changes, then updating changes, then creating changes.
        deleting = []
        updating = []
        creating = []
        for change in changes:
            if change.old == None and change.new != None:
                creating.append(change)
            elif change.old != None and change.new != None:
                updating.append(change)
            elif change.old != None and change.new == None:
                deleting.append(change)
        try:
            for change in deleting:
                entity = change.apply(is_forced=is_forced, moderator=moderator)
                if entity:
                    report['deleted'].append(entity)
            Session.commit()
            for change in updating:
                entity = change.apply(is_forced=is_forced, moderator=moderator)
                if entity:
                    report['updated'].append(entity)
            Session.commit()
            created_entities = []  # Must configure access for new entities.
            for change in creating:
                entity = change.apply(is_forced=is_forced, moderator=moderator)
                if entity:
                    report['created'].append(entity)
                    created_entities.append(entity)
            Session.commit()
        except Exception, inst:
            try:
                from ckan.model import repo as repository
                repository.purge_revision(revision) # Commits and removes session.
            except:
                print "Error: Couldn't purge revision: %s" % revision
            raise inst
        revision_id = revision.id
        # Setup access control for created entities.
        for entity in created_entities:
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
        """Creates changeset from given CKAN repository revision."""
        meta = unicode(self.dumps({
            'log_message': revision.message,
            'author': revision.author,
            'timestamp': revision.timestamp.isoformat(),
        }))
        if follows_id:
            pass
            # Todo: Detect if the new changes conflict with the line (it's a system error).
            # Needed to protect against errors in diff generated by revision comparison.
            # Todo: Calculation of current model state (diff origin to working):
            #        - all values for a single attribute
            #        - all values for a single entity
            #        - all active entity refs
            # Todo: Cache the change entity refs in the changeset to follow refs down a line.
        # Create changes before changeset (changeset id depends on changes).
        changes = []
        for package in revision.packages:
            change = self.construct_package_change(package, revision)
            changes.append(change)
        changeset = self.create_entity(
            follows_id=follows_id,
            meta=meta,
            revision_id=revision.id,
            changes=changes,
        )
        Session.add(changeset)
        Session.commit()
        return changeset.id

    def construct_package_change(self, package, revision):
        """Makes a changeset Change object from a CKAN package instance."""
        packages = PackageRegister()
        vector = packages.diff(package, revision)
        ref = packages.ref(package)
        diff = vector.as_diff()
        change_register = ChangeRegister()
        return change_register.create_entity(ref=ref, diff=diff)

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

    def diff(self, entity, revision=None):
        """Instantiates and returns a Vector for the difference
        between the current and previous Package version."""
        history = entity.all_revisions
        age = len(history)
        current_package_revision = None
        previous_package_revision = None
        for i in range(0, age):
            package_revision = history[i]
            if package_revision.revision.id == revision.id:
                current_package_revision = package_revision
                if i + 1 < age:
                    previous_package_revision = history[i+1]
                break
        if not current_package_revision:
            raise Exception, "Can't find package-revision for package: %s and revision: %s with package history: %s" % (entity, revision, history)
        old_data = None  # Signifies object creation.
        new_data = entity.as_dict()
        del(new_data['revision_id'])
        if previous_package_revision:
            old_data = {}
            for name in entity.revisioned_fields():
                old_value = getattr(previous_package_revision, name)
                new_value = getattr(current_package_revision, name)
                if old_value == new_value:
                    del(new_data[name])
                else:
                    old_data[name] = old_value
                    new_data[name] = new_value
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
        if 'resources' in vector.new:
            entity.resources = []
            for resource_data in vector.new['resources']:
                package_resource = PackageResource(
                    url=resource_data.get('url', u''),
                    format=resource_data.get('format', u''),
                    description=resource_data.get('description', u''),
                    hash=resource_data.get('hash', u''),
                )
                #Session.add(package_resource)
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

