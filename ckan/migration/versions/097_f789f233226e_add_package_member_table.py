# encoding: utf-8

"""Add package_member_table

Revision ID: f789f233226e
Revises: 19ddad52b500
Create Date: 2020-02-09 01:15:12.158897

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = u'f789f233226e'
down_revision = u'19ddad52b500'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        u'package_member',
        sa.Column(u'package_id', sa.UnicodeText()),
        sa.Column(u'user_id', sa.UnicodeText()),
        sa.Column(u'capacity', sa.UnicodeText(), nullable=False),
        sa.Column(u'modified', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint([u'package_id'], [u'package.id'], ),
        sa.ForeignKeyConstraint([u'user_id'], [u'user.id'], ),
        sa.PrimaryKeyConstraint(
            u'package_id', u'user_id', name=u'package_member_pkey')
    )


def downgrade():
    op.drop_table(u'package_member')
