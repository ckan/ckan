# encoding: utf-8
"""008 Update vdm ids

Revision ID: e8283ffb257e
Revises: 1928d4af1cda
Create Date: 2018-09-04 17:43:27.042436

Originally this revision was altering id columns
to UnicodeText
"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'e8283ffb257e'
down_revision = '1928d4af1cda'
branch_labels = None
depends_on = None

foreign_tables = (
    'package', 'package_tag', 'package_revision', 'package_tag_revision',
    'package_extra', 'package_extra_revision'
)


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    for table in foreign_tables:
        op.drop_column(table, 'revision_id')
    op.alter_column(
        'revision', 'id', type_=sa.UnicodeText, server_default=None
    )
    for table in foreign_tables:
        op.add_column(
            table,
            sa.Column(
                'revision_id', sa.UnicodeText, sa.ForeignKey('revision.id')
            )
        )


def downgrade():
    for table in foreign_tables:
        op.drop_column(table, 'revision_id')
    op.drop_column('revision', 'id')
    op.add_column(
        'revision',
        sa.Column(
            'id', sa.Integer, primary_key=True, nullable=False, unique=True
        )
    )

    for table in foreign_tables:
        op.add_column(
            table,
            sa.Column('revision_id', sa.Integer, sa.ForeignKey('revision.id'))
        )
