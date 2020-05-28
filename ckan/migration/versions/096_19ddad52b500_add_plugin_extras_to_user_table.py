# encoding: utf-8
"""Add plugin_extras to user table

Revision ID: 19ddad52b500
Revises: 9fadda785b07
Create Date: 2020-05-12 22:19:37.878470

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = u'19ddad52b500'
down_revision = u'9fadda785b07'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        u'user',
        sa.Column(
            u'plugin_extras',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True)
    )


def downgrade():
    op.drop_column(u'user', u'plugin_extras')
