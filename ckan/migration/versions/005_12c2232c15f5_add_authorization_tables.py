# encoding: utf-8
"""005 Add authorization tables

Revision ID: 12c2232c15f5
Revises: f92ee205e46d
Create Date: 2018-09-04 17:34:59.667587

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '12c2232c15f5'
down_revision = 'f92ee205e46d'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.create_table(
        'role_action',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('role', sa.UnicodeText),
        sa.Column('context', sa.UnicodeText, nullable=False),
        sa.Column('action', sa.UnicodeText),
    )

    op.create_table(
        'user_object_role', sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('user_id', sa.UnicodeText, sa.ForeignKey('user.id')),
        sa.Column('context', sa.UnicodeText, nullable=False),
        sa.Column('role', sa.UnicodeText)
    )

    op.create_table(
        'package_role',
        sa.Column(
            'user_object_role_id',
            sa.UnicodeText,
            sa.ForeignKey('user_object_role.id'),
            primary_key=True
        ),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
    )

    op.create_table(
        'group_role',
        sa.Column(
            'user_object_role_id',
            sa.UnicodeText,
            sa.ForeignKey('user_object_role.id'),
            primary_key=True
        ),
        sa.Column('group_id', sa.UnicodeText, sa.ForeignKey('group.id')),
    )


def downgrade():
    op.drop_table('group_role')
    op.drop_table('package_role')
    op.drop_table('user_object_role')
    op.drop_table('role_action')
