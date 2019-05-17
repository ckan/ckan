# encoding: utf-8
"""060 Add system info table

Revision ID: 31ad11c518fc
Revises: 9291bb46f352
Create Date: 2018-09-04 18:49:09.587220

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '31ad11c518fc'
down_revision = '9291bb46f352'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.create_table(
        'system_info',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('key', sa.Unicode(100), unique=True, nullable=False),
        sa.Column('value', sa.UnicodeText),
        sa.Column('revision_id', sa.UnicodeText, sa.ForeignKey('revision.id'))
    )

    op.create_table(
        'system_info_revision',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('key', sa.Unicode(100), unique=True, nullable=False),
        sa.Column('value', sa.UnicodeText),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.Integer, sa.ForeignKey('system_info.id')
        ),
    )


def downgrade():
    op.drop_table('system_info_revision')
    op.drop_table('system_info')
