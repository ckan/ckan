# encoding: utf-8
"""035 Harvesting doc versioning

Revision ID: 81148ccebd6c
Revises: 6c600693af5b
Create Date: 2018-09-04 18:49:01.017635

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '81148ccebd6c'
down_revision = '6c600693af5b'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'harvested_document_revision',
        sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('guid', sa.UnicodeText), sa.Column('created', sa.TIMESTAMP),
        sa.Column('content', sa.UnicodeText, nullable=False),
        sa.Column('source_id', sa.UnicodeText),
        sa.Column('package_id', sa.UnicodeText),
        sa.Column('state', sa.UnicodeText),
        sa.Column('revision_id', sa.UnicodeText, nullable=False),
        sa.Column('continuity_id', sa.UnicodeText)
    )

    op.add_column('harvested_document', sa.Column('state', sa.UnicodeText))
    op.add_column(
        'harvested_document', sa.Column('revision_id', sa.UnicodeText)
    )

    op.create_primary_key(
        'harvested_document_revision_pkey', 'harvested_document_revision',
        ['id', 'revision_id']
    )
    op.create_foreign_key(
        'harvested_document_revision_id_fkey', 'harvested_document',
        'revision', ['revision_id'], ['id']
    )
    op.create_foreign_key(
        'harvested_document_revision_continuity_id_fkey',
        'harvested_document_revision', 'harvested_document', ['continuity_id'],
        ['id']
    )
    op.create_foreign_key(
        'harvested_document_revision_package_id_fkey',
        'harvested_document_revision', 'package', ['package_id'], ['id']
    )

    op.create_foreign_key(
        'harvested_document_revision_revision_id_fkey',
        'harvested_document_revision', 'revision', ['revision_id'], ['id']
    )
    op.create_foreign_key(
        'harvested_document_revision_source_id_fkey',
        'harvested_document_revision', 'harvest_source', ['source_id'], ['id']
    )


def downgrade():
    op.drop_constraint(
        'harvested_document_revision_source_id_fkey',
        'harvested_document_revision'
    )
    op.drop_constraint(
        'harvested_document_revision_revision_id_fkey',
        'harvested_document_revision'
    )
    op.drop_constraint(
        'harvested_document_revision_package_id_fkey',
        'harvested_document_revision'
    )
    op.drop_constraint(
        'harvested_document_revision_continuity_id_fkey',
        'harvested_document_revision'
    )
    op.drop_constraint(
        'harvested_document_revision_id_fkey', 'harvested_document'
    )
    op.drop_constraint(
        'harvested_document_revision_pkey', 'harvested_document_revision'
    )

    op.drop_column('harvested_document', 'state')
    op.drop_column('harvested_document', 'revision_id')

    op.drop_table('harvested_document_revision')
