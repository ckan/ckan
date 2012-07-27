from sqlalchemy import types, Column, Table

import meta
import core
import domain_object

__all__ = ['system_info_revision_table', 'system_info_table', 'SystemInfo']

system_info_table = Table('system_info', meta.metadata,
        Column('id', types.Integer() ,  primary_key=True, nullable=False),
        Column('key', types.Unicode(100), unique=True, nullable=False),
        Column('value', types.UnicodeText),
    )

system_info_revision_table = core.make_revisioned_table(system_info_table)

class SystemInfo(domain_object.DomainObject):

    def __init__(self, key, value):
        self.key = key
        self.value = unicode(value)


meta.mapper(SystemInfo, system_info_table)
