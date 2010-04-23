from sqlalchemy import *
from migrate import *
import datetime
from migrate.changeset.constraint import PrimaryKeyConstraint

metadata = MetaData(migrate_engine)

revision_table = Table('revision', metadata,
        Column('id', UnicodeText, primary_key=True),
)

changeset_table = Table('changeset', metadata,
        Column('id', UnicodeText, primary_key=True),
        Column('closes_id', UnicodeText, nullable=True),
        Column('follows_id', UnicodeText, nullable=True),
        Column('meta', UnicodeText, nullable=True),
        Column('branch', UnicodeText, nullable=True),
        Column('timestamp', DateTime, default=datetime.datetime.utcnow),
        Column('is_working', Boolean, default=False),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), nullable=True),
        Column('status', UnicodeText, nullable=True),
        Column('added_here', DateTime, default=datetime.datetime.utcnow),
)

change_table = Table('change', metadata,
        Column('ref', UnicodeText, nullable=True),
        Column('diff', UnicodeText, nullable=True),
        Column('changeset_id', UnicodeText, ForeignKey('changeset.id')),
)

changemask_table = Table('changemask', metadata,
        Column('ref', UnicodeText, primary_key=True),
        Column('timestamp', DateTime, default=datetime.datetime.utcnow),
)


def upgrade():
    changeset_table.create()
    change_table.create()

def downgrade():
    change_table.drop()
    changeset_table.drop()

