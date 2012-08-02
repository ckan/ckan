from sqlalchemy import types, Column, Table

import meta
import core
import domain_object

__all__ = ['system_info_revision_table', 'system_info_table', 'SystemInfo',
          'get_system_info', 'set_system_info']

system_info_table = Table('system_info', meta.metadata,
        Column('id', types.Integer(),  primary_key=True, nullable=False),
        Column('key', types.Unicode(100), unique=True, nullable=False),
        Column('value', types.UnicodeText),
    )

system_info_revision_table = core.make_revisioned_table(system_info_table)


class SystemInfo(domain_object.DomainObject):

    def __init__(self, key, value):
        self.key = key
        self.value = unicode(value)


meta.mapper(SystemInfo, system_info_table)


def get_system_info(key, default=None):
    ''' get data from system_info table '''
    obj = meta.Session.query(SystemInfo).filter_by(key=key).first()
    if obj:
        return obj.value
    else:
        return default


def delete_system_info(key, default=None):
    ''' delete data from system_info table '''
    obj = meta.Session.query(SystemInfo).filter_by(key=key).first()
    if obj:
        meta.Session.delete(obj)
        meta.Session.commit()


def set_system_info(key, value):
    ''' save data in the system_info table '''

    obj = None
    obj = meta.Session.query(SystemInfo).filter_by(key=key).first()
    if obj and obj.value == unicode(value):
        return
    if not obj:
        obj = SystemInfo(key, value)
    else:
        obj.value = unicode(value)
    meta.Session.add(obj)
    meta.Session.commit()
