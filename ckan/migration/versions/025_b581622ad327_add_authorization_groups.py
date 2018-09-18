# encoding: utf-8
"""025 Add authorization groups

Revision ID: b581622ad327
Revises: 12981fe12484
Create Date: 2018-09-04 18:48:57.649187

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'b581622ad327'
down_revision = '12981fe12484'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'authorization_group',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('name', sa.UnicodeText),
        sa.Column(
            'created', sa.DateTime, server_default=sa.func.current_timestamp()
        ),
    )

    op.create_table(
        'authorization_group_user',
        sa.Column(
            'authorization_group_id',
            sa.UnicodeText,
            sa.ForeignKey('authorization_group.id'),
            nullable=False
        ),
        sa.Column(
            'user_id',
            sa.UnicodeText,
            sa.ForeignKey('user.id'),
            nullable=False
        )
    )
    # make user nullable:
    op.alter_column('user_object_role', 'user_id', nullable=True)

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
        ),
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


def downgrade():
    op.drop_column('user_object_role', 'authorized_group_id')
    op.drop_table('authorization_group_role')
    op.alter_column('user_object_role', 'user_id', nullable=False)
    op.drop_table('authorization_group_user')
    op.drop_table('authorization_group')
