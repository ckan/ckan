"""079 Resource revision index

Revision ID: e0177a15d2c9
Revises: ae821876532a
Create Date: 2018-09-04 18:49:16.198887

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e0177a15d2c9'
down_revision = 'ae821876532a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'idx_resource_continuity_id', 'resource_revision', ['continuity_id']
    )


def downgrade():
    op.drop_index('idx_resource_continuity_id', 'resource_revision')
