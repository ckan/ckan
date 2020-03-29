# encoding: utf-8

"""Add package_member_table

Revision ID: f789f233226e
Revises: d4d9be9189fe
Create Date: 2020-02-09 01:15:12.158897

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = u'f789f233226e'
down_revision = u'588d7cfb9a41'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        u'package_member',
        sa.Column(u'id', sa.UnicodeText(), nullable=False),
        sa.Column(u'package_id', sa.UnicodeText(), nullable=True),
        sa.Column(u'user_id', sa.UnicodeText(), nullable=True),
        sa.Column(u'capacity', sa.UnicodeText(), nullable=False),
        sa.Column(u'modified', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint([u'package_id'], [u'package.id'], ),
        sa.ForeignKeyConstraint([u'user_id'], [u'user.id'], ),
        sa.PrimaryKeyConstraint(u'id')
    )


def downgrade():
    op.drop_table(u'package_member')
