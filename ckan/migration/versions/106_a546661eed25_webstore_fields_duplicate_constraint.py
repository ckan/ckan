"""remove webstore fields, duplicate constraint

Revision ID: a546661eed25
Revises: ed69a17ba4a5
Create Date: 2024-06-05 18:23:02.915484

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a546661eed25'
down_revision = 'ed69a17ba4a5'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('resource', 'webstore_last_updated')
    op.drop_column('resource', 'webstore_url')
    op.drop_constraint('resource_view_resource_id_fkey1', 'resource_view',
                       type_='foreignkey')


def downgrade():
    op.create_foreign_key('resource_view_resource_id_fkey1', 'resource_view',
                          'resource', ['resource_id'], ['id'])
    op.add_column('resource', sa.Column('webstore_url', sa.TEXT(),
                  autoincrement=False, nullable=True))
    op.add_column('resource', sa.Column('webstore_last_updated',
                  postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
