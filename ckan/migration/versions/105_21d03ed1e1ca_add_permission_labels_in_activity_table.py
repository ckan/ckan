# encoding: utf-8

"""Add permission labels in activity table

Revision ID: 21d03ed1e1ca
Revises: 9f33a0280c51
Create Date: 2023-04-26 14:06:05.086247

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '21d03ed1e1ca'
down_revision = '9f33a0280c51'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('activity', sa.Column(
        'permission_labels', sa.ARRAY(sa.Text)))


def downgrade():
    op.drop_column('activity', 'permission_labels')
