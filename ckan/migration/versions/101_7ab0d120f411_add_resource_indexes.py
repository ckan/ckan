"""add resource indexes

Revision ID: 7ab0d120f411
Revises: ccd38ad5fced
Create Date: 2021-11-11 14:12:09.088843

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ab0d120f411'
down_revision = 'ccd38ad5fced'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_index(
        'idx_package_resource_revision_period', 'resource_revision', ['package_id', 'revision_timestamp', 'expired_timestamp']
    )


def downgrade():
    op.drop_index('idx_resource_continuity_id', 'resource_revision')
