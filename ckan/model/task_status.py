from datetime import datetime
from sqlalchemy import types, Column, Table, UniqueConstraint

import meta
import types as _types
import domain_object

__all__ = ['TaskStatus', 'task_status_table']

task_status_table = Table('task_status', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('entity_id', types.UnicodeText, nullable=False),
    Column('entity_type', types.UnicodeText, nullable=False),
    Column('task_type', types.UnicodeText, nullable=False),
    Column('key', types.UnicodeText, nullable=False),
    Column('value', types.UnicodeText, nullable=False),
    Column('state', types.UnicodeText),
    Column('error', types.UnicodeText),
    Column('last_updated', types.DateTime, default=datetime.now),
    UniqueConstraint('entity_id', 'task_type', 'key')
)

class TaskStatus(domain_object.DomainObject):
    @classmethod
    def get(cls, reference):
        '''Returns a task status object referenced by its id.'''
        query = meta.Session.query(cls).filter(cls.id==reference)
        return query.first()

meta.mapper(TaskStatus, task_status_table)
