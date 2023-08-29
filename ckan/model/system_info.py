# encoding: utf-8

'''
The system_info table and SystemInfo mapped class store runtime-editable
configuration options.

For more details, check :doc:`maintaining/configuration`.
'''

from typing import Any, Optional

from sqlalchemy import types, Column, Table
from sqlalchemy.exc import ProgrammingError


import ckan.model.meta as meta
import ckan.model.core as core
import ckan.model.domain_object as domain_object

__all__ = ['system_info_table', 'SystemInfo',
           'get_system_info', 'set_system_info']

system_info_table = Table(
    'system_info', meta.metadata,
    Column('id', types.Integer(),  primary_key=True, nullable=False),
    Column('key', types.Unicode(100), unique=True, nullable=False),
    Column('value', types.UnicodeText),
    Column('state', types.UnicodeText, default=core.State.ACTIVE),
)


class SystemInfo(core.StatefulObjectMixin,
                 domain_object.DomainObject):
    id: int
    key: str
    value: str
    state: str

    def __init__(self, key: str, value: Any) -> None:

        super(SystemInfo, self).__init__()

        self.key = key
        self.value = str(value)


meta.mapper(SystemInfo, system_info_table)


def get_system_info(key: str, default: Optional[str]=None) -> Optional[str]:
    ''' get data from system_info table '''
    try:
        obj = meta.Session.query(SystemInfo).filter_by(key=key).first()
        meta.Session.commit()
        if obj:
            return obj.value
    except ProgrammingError:
        meta.Session.rollback()
    return default



def delete_system_info(key: str) -> None:
    ''' delete data from system_info table '''
    obj = meta.Session.query(SystemInfo).filter_by(key=key).first()
    if obj:
        meta.Session.delete(obj)
        meta.Session.commit()


def set_system_info(key: str, value: str) -> bool:
    ''' save data in the system_info table '''
    obj = None
    obj = meta.Session.query(SystemInfo).filter_by(key=key).first()
    if obj and obj.value == str(value):
        return False
    if not obj:
        obj = SystemInfo(key, value)
    else:
        obj.value = str(value)

    meta.Session.add(obj)
    meta.Session.commit()
    return True
