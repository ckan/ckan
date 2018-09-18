# encoding: utf-8
"""020 Add changeset

Revision ID: 69a0b0efc609
Revises: b2eb6f34a638
Create Date: 2018-09-04 18:48:54.952113

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '69a0b0efc609'
down_revision = 'b2eb6f34a638'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
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


def downgrade():
    op.drop_table('changeset')
    op.drop_table('change')
    op.drop_table('changemask')
