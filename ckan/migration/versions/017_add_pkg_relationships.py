from sqlalchemy import *
from migrate import *
import uuid

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

package_table = Table('package', metadata, autoload=True)

package_relationship_table = Table('package_relationship', metadata,
     Column('id', UnicodeText, primary_key=True, default=make_uuid),
     Column('subject_package_id', UnicodeText, ForeignKey('package.id')),
     Column('object_package_id', UnicodeText, ForeignKey('package.id')),
     Column('type', UnicodeText),
     Column('comment', UnicodeText),
     Column('revision_id', UnicodeText, ForeignKey('revision.id'))
     )

package_relationship_revision_table = Table('package_relationship_revision', metadata,
     Column('id', UnicodeText, primary_key=True, default=make_uuid),
     Column('subject_package_id', UnicodeText, ForeignKey('package.id')),
     Column('object_package_id', UnicodeText, ForeignKey('package.id')),
     Column('type', UnicodeText),
     Column('comment', UnicodeText),
     Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
     Column('continuity_id', UnicodeText, ForeignKey('package_relationship.id'))
    )

def upgrade():
    package_relationship_table.create()
    package_relationship_revision_table.create()

def downgrade():
    raise NotImplementedError()
