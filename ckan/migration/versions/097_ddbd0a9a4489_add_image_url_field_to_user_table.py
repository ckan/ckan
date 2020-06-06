# encoding: utf-8
"""Add image_url field to user table

Revision ID: ddbd0a9a4489
Revises: 19ddad52b500
Create Date: 2020-06-05 23:30:09.595981

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ddbd0a9a4489'
down_revision = u'19ddad52b500'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column(
            'image_url',
            sa.UnicodeText
        )
    )


def downgrade():
    op.drop_column('user', 'image_url')
