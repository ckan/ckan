# encoding: utf-8

"""Add last_active column in user table

Revision ID: d111f446733b
Revises: ccd38ad5fced
Create Date: 2021-09-22 00:44:40.777435

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd111f446733b'
down_revision = 'ccd38ad5fced'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('last_active', sa.TIMESTAMP))


def downgrade():
    op.drop_column('user', 'last_active')
