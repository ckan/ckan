# encoding: utf-8
"""038 Delete migration tables

Revision ID: fd6622e3d964
Revises: edcf3b8c3c1b
Create Date: 2018-09-04 18:49:02.023123

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'fd6622e3d964'
down_revision = 'edcf3b8c3c1b'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.drop_table('harvested_document_revision')
    op.drop_table('harvested_document')
    op.drop_table('harvesting_job')
    op.drop_table('harvest_source')


def downgrade():
    op.create_table(
        'harvest_source',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('status', sa.UnicodeText, server_default=u'New'),
        sa.Column('url', sa.UnicodeText, unique=True, nullable=False),
        sa.Column('description', sa.UnicodeText, default=u''),
        sa.Column('user_ref', sa.UnicodeText, default=u''),
        sa.Column('publisher_ref', sa.UnicodeText, default=u''),
        sa.Column(
            'created', sa.DateTime, server_default=sa.func.current_timestamp()
        ),
    )

    op.create_table(
        'harvesting_job',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('status', sa.UnicodeText, default=u'', nullable=False),
        sa.Column(
            'created', sa.DateTime, server_default=sa.func.current_timestamp()
        ),
        sa.Column('user_ref', sa.UnicodeText, nullable=False),
        sa.Column('report', sa.UnicodeText, default=u''),
        sa.Column(
            'source_id', sa.UnicodeText, sa.ForeignKey('harvest_source.id')
        ),
    )

    op.create_table(
        'harvested_document',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('created', sa.DateTime),
        sa.Column('content', sa.UnicodeText, nullable=False),
        sa.Column('source_id', sa.UnicodeText),
        sa.Column('package_id', sa.UnicodeText),
        sa.Column('state', sa.UnicodeText),
        sa.Column('revision_id', sa.UnicodeText, nullable=False),
        sa.Column('guid', sa.UnicodeText),
        sa.Column('created', sa.TIMESTAMP),
    )

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
