# encoding: utf-8
"""078 Remove old authz model

Revision ID: ae821876532a
Revises: 51171a04d86d
Create Date: 2018-09-04 18:49:15.812926

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'ae821876532a'
down_revision = '51171a04d86d'
branch_labels = None
depends_on = None

indexes = (
    ('idx_uor_id', 'user_object_role', ['id']),
    ('idx_uor_user_id', 'user_object_role', ['user_id']),
    ('idx_uor_context', 'user_object_role', ['context']),
    ('idx_uor_role', 'user_object_role', ['role']),
    ('idx_uor_user_id_role', 'user_object_role', ['user_id', 'role']),
    ('idx_ra_role', 'role_action', ['role']),
    ('idx_ra_action', 'role_action', ['action']),
    ('idx_ra_role_action', 'role_action', ['action', 'role']),
)


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.drop_table('role_action')
    op.drop_table('package_role')
    op.drop_table('group_role')
    op.drop_table('system_role')
    op.drop_table('authorization_group_role')
    op.drop_table('user_object_role')


def downgrade():

    op.create_table(
        'user_object_role', sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('user_id', sa.UnicodeText, sa.ForeignKey('user.id')),
        sa.Column('context', sa.UnicodeText, nullable=False),
        sa.Column('role', sa.UnicodeText)
    )

    op.create_table(
        'authorization_group_role',
        sa.Column(
            'user_object_role_id',
            sa.UnicodeText,
            sa.ForeignKey('user_object_role.id'),
            primary_key=True
        ),
        sa.Column(
            'authorization_group_id', sa.UnicodeText,
            sa.ForeignKey('authorization_group.id')
        )
    )

    op.create_table(
        'system_role',
        sa.Column(
            'user_object_role_id',
            sa.UnicodeText,
            sa.ForeignKey('user_object_role.id'),
            primary_key=True
        ),
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

    op.create_table(
        'package_role',
        sa.Column(
            'user_object_role_id',
            sa.UnicodeText,
            sa.ForeignKey('user_object_role.id'),
            primary_key=True
        ),
        sa.Column('package_id', sa.UnicodeText, sa.ForeignKey('package.id')),
    )

    op.create_table(
        'role_action',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('role', sa.UnicodeText),
        sa.Column('context', sa.UnicodeText, nullable=False),
        sa.Column('action', sa.UnicodeText),
    )

    op.add_column(
        'user_object_role',
        sa.Column(
            'authorized_group_id',
            sa.UnicodeText,
            sa.ForeignKey('authorization_group.id'),
            nullable=True
        )
    )
    for name, table, columns in indexes:
        op.create_index(name, table, columns)
