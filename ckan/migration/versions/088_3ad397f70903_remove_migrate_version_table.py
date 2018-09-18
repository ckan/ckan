# encoding: utf-8
"""Remove migrate version table

Revision ID: 3ad397f70903
Revises: ff1b303cab77
Create Date: 2018-09-18 18:16:50.083513

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '3ad397f70903'
down_revision = 'ff1b303cab77'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('DROP TABLE IF EXISTS migrate_version')


def downgrade():
    pass
