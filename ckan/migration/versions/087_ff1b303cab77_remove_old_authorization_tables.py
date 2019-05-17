# encoding: utf-8
"""087 Remove old authorization tables

Revision ID: ff1b303cab77
Revises: 19663581b3bb
Create Date: 2018-09-04 18:49:18.998454

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version

# revision identifiers, used by Alembic.
revision = 'ff1b303cab77'
down_revision = '19663581b3bb'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.drop_table('authorization_group_user')
    op.drop_table('authorization_group')


def downgrade():
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
        ), sa.Column('id', sa.UnicodeText, primary_key=True)
    )
