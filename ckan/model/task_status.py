import sqlalchemy as sa
from meta import *
from core import *
import types as _types
import domain_object
# se overwrite datetime somewhere in our importing
from datetime import datetime

__all__ = ['TaskStatus', 'task_status_table']

task_status_table = Table('task_status', metadata,
    Column('id', UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('entity_id', UnicodeText, nullable=False),
    Column('entity_type', UnicodeText, nullable=False),
    Column('task_type', UnicodeText, nullable=False),
    Column('key', UnicodeText, nullable=False),
    Column('value', UnicodeText, nullable=False),
    Column('state', UnicodeText),
    Column('error', UnicodeText),
    Column('last_updated', DateTime, default=datetime.now),
    sa.UniqueConstraint('entity_id', 'task_type', 'key')
)

class TaskStatus(domain_object.DomainObject):
    @classmethod
    def get(cls, reference):
        '''Returns a task status object referenced by its id.'''
        query = Session.query(cls).filter(cls.id==reference)
        return query.first()

mapper(TaskStatus, task_status_table)
