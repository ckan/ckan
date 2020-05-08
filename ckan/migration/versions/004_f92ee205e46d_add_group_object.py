# encoding: utf-8
"""Add group object

Revision ID: f92ee205e46d
Revises: f22b4f5241a5
Create Date: 2018-09-04 17:22:50.675045

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'f92ee205e46d'
down_revision = 'f22b4f5241a5'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.create_table(
        'group',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('name', sa.UnicodeText, unique=True, nullable=False),
        sa.Column('title', sa.UnicodeText),
        sa.Column('description', sa.UnicodeText),
    )

    op.create_table(
        'package_group',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('group_id', sa.UnicodeText, sa.ForeignKey('group.id')),
    )


def downgrade():
    op.drop_table('package_group')
    op.drop_table('group')
