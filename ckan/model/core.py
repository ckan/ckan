# encoding: utf-8

import datetime

import domain_object
import meta
import vdm.sqlalchemy
from sqlalchemy import Column, DateTime, Text, Boolean


__all__ = ['System', 'Revision', 'State', 'revision_table']

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
State = vdm.sqlalchemy.State
State.all = [State.ACTIVE, State.DELETED]
Revision = vdm.sqlalchemy.make_Revision(meta.mapper, revision_table)


def make_revisioned_table(table):
    revision_table = vdm.sqlalchemy.make_revisioned_table(table)
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
