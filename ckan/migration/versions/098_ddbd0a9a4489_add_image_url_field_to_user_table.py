# encoding: utf-8
"""Add image_url field to user table

Revision ID: ddbd0a9a4489
Revises: f789f233226e
Create Date: 2020-06-05 23:30:09.595981

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = u'ddbd0a9a4489'
down_revision = u'f789f233226e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        u'user',
        sa.Column(
            u'image_url',
            sa.UnicodeText
        )
    )


def downgrade():
    op.drop_column(u'user', u'image_url')
