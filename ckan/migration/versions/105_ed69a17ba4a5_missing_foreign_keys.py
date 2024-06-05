"""missing foreign keys

Revision ID: ed69a17ba4a5
Revises: 9f33a0280c51
Create Date: 2024-06-05 14:24:19.133997

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'ed69a17ba4a5'
down_revision = '9f33a0280c51'
branch_labels = None
depends_on = None


def upgrade():
    op.create_foreign_key(None, 'resource', 'package', ['package_id'], ['id'])
    op.create_foreign_key(None, 'resource_view', 'resource', ['resource_id'],
                          ['id'])


def downgrade():
    op.drop_constraint(None, 'resource_view', type_='foreignkey')
    op.drop_constraint(None, 'resource', type_='foreignkey')
