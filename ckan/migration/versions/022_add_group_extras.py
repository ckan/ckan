from sqlalchemy import *
from migrate import *
import migrate.changeset
import vdm.sqlalchemy
import uuid
from sqlalchemy import types

from ckan.lib.helpers import json
class JsonType(types.TypeDecorator):
    '''Store data as JSON serializing on save and unserializing on use.
    '''
    impl = types.UnicodeText

    def process_bind_param(self, value, engine):
        if value is None or value == {}: # ensure we stores nulls in db not json "null"
            return None
        else:
            # ensure_ascii=False => allow unicode but still need to convert
            return unicode(json.dumps(value, ensure_ascii=False))

    def process_result_value(self, value, engine):
        if value is None:
            return None
        else:
            return json.loads(value)

    def copy(self):
        return JsonType(self.impl.length)

def make_uuid():
    return unicode(uuid.uuid4())



def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

    group_table = Table('group', metadata, autoload=True)
    group_extra_table = Table('group_extra', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('group_id', UnicodeText, ForeignKey('group.id')),
        Column('key', UnicodeText),
        Column('value', JsonType),
    )
    
    group_extra_table.create()

def downgrade(migrate_engine):
    raise NotImplementedError()
