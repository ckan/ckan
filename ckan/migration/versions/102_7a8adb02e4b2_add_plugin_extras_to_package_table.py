"""Add plugin_extras to package table

Revision ID: 7a8adb02e4b2
Revises: d111f446733b
Create Date: 2022-06-15 11:11:50.142573

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7a8adb02e4b2'
down_revision = 'd111f446733b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        u'package',
        sa.Column(
            u'plugin_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True)
    )


def downgrade():
    op.drop_column(u'package', u'plugin_data')
