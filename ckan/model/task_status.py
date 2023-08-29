# encoding: utf-8

from datetime import datetime
from typing import Optional
from sqlalchemy import types, Column, Table, UniqueConstraint
from typing_extensions import Self

import ckan.model.meta as meta
import ckan.model.types as _types
import ckan.model.domain_object as domain_object

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
    id: str
    entity_id: str
    entuty_type: str
    task_type: str
    key: str
    value: str
    state: str
    error: str
    last_updated: datetime

    @classmethod
    def get(cls, reference: str) -> Optional[Self]:
        '''Returns a task status object referenced by its id.'''
        if not reference:
            return None

        task = meta.Session.query(cls).get(reference)
        return task

meta.mapper(TaskStatus, task_status_table)
