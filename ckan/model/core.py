# encoding: utf-8

import datetime

from sqlalchemy import Column, DateTime, Text, Boolean
import vdm.sqlalchemy

import domain_object
import meta
import revision


__all__ = ['System', 'Revision', 'State', 'StatefulObjectMixin',
           'revision_table']
log = __import__('logging').getLogger(__name__)

# VDM-specific tables
revision_table = vdm.sqlalchemy.make_revision_table(meta.metadata)
revision_table.append_column(Column('approved_timestamp', DateTime))


class System(domain_object.DomainObject):

    name = 'system'

    def __unicode__(self):
        return u'<%s>' % self.__class__.__name__

    def purge(self):
        pass

    @classmethod
    def by_name(cls, name):
        return System()


# VDM-specific domain objects
class State(object):
    ACTIVE = u'active'
    DELETED = u'deleted'
    PENDING = u'pending'


class StatefulObjectMixin(object):
    __stateful__ = True

    def delete(self):
        log.debug('Running delete on %s', self)
        self.state = State.DELETED

    def undelete(self):
        self.state = State.ACTIVE

    def is_active(self):
        # also support None in case this object is not yet refreshed ...
        return self.state is None or self.state == State.ACTIVE


Revision = vdm.sqlalchemy.make_Revision(meta.mapper, revision_table)


def make_revisioned_table(table, frozen=False):
    revision_table = revision.make_revisioned_table(table, frozen)
    revision_table.append_column(Column('expired_id',
                                 Text))
    revision_table.append_column(Column('revision_timestamp', DateTime))
    revision_table.append_column(Column('expired_timestamp', DateTime,
                                 default=datetime.datetime(9999, 12, 31)))
    revision_table.append_column(Column('current', Boolean))
    # NB columns 'current' and 'expired_id' are deprecated and not used
    # TODO remove them at a later version
    # (expired_timestamp is still used when showing old versions of a dataset)
    return revision_table
