# encoding: utf-8

'''
The system_info table and SystemInfo mapped class store runtime-editable
configuration options.

For more details, check :doc:`maintaining/configuration`.
'''

from sqlalchemy import types, Column, Table

import vdm.sqlalchemy
import meta
import core
import domain_object

__all__ = ['system_info_revision_table', 'system_info_table', 'SystemInfo',
           'SystemInfoRevision', 'get_system_info', 'set_system_info']

system_info_table = Table(
    'system_info', meta.metadata,
    Column('id', types.Integer(),  primary_key=True, nullable=False),
    Column('key', types.Unicode(100), unique=True, nullable=False),
    Column('value', types.UnicodeText),
)

vdm.sqlalchemy.make_table_stateful(system_info_table)
system_info_revision_table = core.make_revisioned_table(system_info_table)


class SystemInfo(vdm.sqlalchemy.RevisionedObjectMixin,
                 vdm.sqlalchemy.StatefulObjectMixin,
                 domain_object.DomainObject):

    def __init__(self, key, value):

        super(SystemInfo, self).__init__()

        self.key = key
        self.value = unicode(value)


meta.mapper(SystemInfo, system_info_table,
            extension=[
                vdm.sqlalchemy.Revisioner(system_info_revision_table),
                ])

vdm.sqlalchemy.modify_base_object_mapper(SystemInfo, core.Revision, core.State)
SystemInfoRevision = vdm.sqlalchemy.create_object_version(meta.mapper,
                                                          SystemInfo,
                                                          system_info_revision_table)


def get_system_info(key, default=None):
    ''' get data from system_info table '''
    from sqlalchemy.exc import ProgrammingError
    try:
        obj = meta.Session.query(SystemInfo).filter_by(key=key).first()
        if obj:
            return obj.value
    except ProgrammingError:
        meta.Session.rollback()
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

    from ckan.model import repo
    rev = repo.new_revision()
    rev.message = 'Set {0} setting in system_info table'.format(key)
    meta.Session.add(obj)
    meta.Session.commit()

    return True
