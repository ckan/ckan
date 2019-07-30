# encoding: utf-8
"""046 Drop changesets

Revision ID: b69e9b80396f
Revises: 54e3f155d945
Create Date: 2018-09-04 18:49:04.791120

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'b69e9b80396f'
down_revision = '54e3f155d945'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.drop_table('change')
    op.drop_table('changemask')
    op.drop_table('changeset')


def downgrade():
    op.create_table(
        'changeset',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('closes_id', sa.UnicodeText, nullable=True),
        sa.Column('follows_id', sa.UnicodeText, nullable=True),
        sa.Column('meta', sa.UnicodeText, nullable=True),
        sa.Column('branch', sa.UnicodeText, nullable=True),
        sa.Column(
            'timestamp',
            sa.DateTime,
            server_default=sa.func.current_timestamp()
        ),
        sa.Column('is_working', sa.Boolean, default=False),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            nullable=True
        ),
        sa.Column(
            'added_here',
            sa.DateTime,
            server_default=sa.func.current_timestamp()
        ),
    )

    op.create_table(
        'change',
        sa.Column('ref', sa.UnicodeText, nullable=True),
        sa.Column('diff', sa.UnicodeText, nullable=True),
        sa.Column(
            'changeset_id', sa.UnicodeText, sa.ForeignKey('changeset.id')
        ),
    )

    op.create_table(
        'changemask',
        sa.Column('ref', sa.UnicodeText, primary_key=True),
        sa.Column(
            'timestamp',
            sa.DateTime,
            server_default=sa.func.current_timestamp()
        ),
    )
