"""empty message

Revision ID: e12e991f586b
Revises: f7b64c701a10
Create Date: 2026-02-10 18:26:31.122945

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e12e991f586b'
down_revision = 'f7b64c701a10'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "idx_package_resource_unique_position", "resource",
        [sa.Column('package_id'), sa.Column('position')],
        unique=True, postgresql_where=sa.text('"resource".state=\'active\''))
    print('Created "idx_package_resource_unique_position" index')


def downgrade():
    op.drop_index("idx_package_resource_unique_position")
    print('Dropped "idx_package_resource_unique_position" index')
