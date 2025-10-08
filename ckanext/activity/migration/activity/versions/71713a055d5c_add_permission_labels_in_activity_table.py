# encoding: utf-8

"""Add permission labels in activity table

Revision ID: 71713a055d5c
Revises:
Create Date: 2023-07-26 05:35:58.228599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71713a055d5c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('activity', sa.Column(
        'permission_labels', sa.ARRAY(sa.Text)))


def downgrade():
    op.drop_column('activity', 'permission_labels')
