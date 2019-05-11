# encoding: utf-8
"""056 Add related table

Revision ID: 11af3215ae89
Revises: 048f7db947bf
Create Date: 2018-09-04 18:49:08.239860

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '11af3215ae89'
down_revision = '048f7db947bf'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'related', sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('type', sa.UnicodeText, nullable=False),
        sa.Column('title', sa.UnicodeText),
        sa.Column('description', sa.UnicodeText),
        sa.Column('image_url', sa.UnicodeText),
        sa.Column('url', sa.UnicodeText), sa.Column('created', sa.TIMESTAMP),
        sa.Column('owner_id', sa.UnicodeText)
    )
    op.create_table(
        'related_dataset', sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('dataset_id', sa.UnicodeText, nullable=False),
        sa.Column('related_id', sa.UnicodeText, nullable=False),
        sa.Column('status', sa.UnicodeText)
    )
    op.create_primary_key('related_pkey', 'related', ['id'])
    op.create_primary_key('related_dataset_pkey', 'related_dataset', ['id'])

    op.create_foreign_key(
        'related_dataset_dataset_id_fkey', 'related_dataset', 'package',
        ['dataset_id'], ['id']
    )
    op.create_foreign_key(
        'related_dataset_related_id_fkey', 'related_dataset', 'related',
        ['related_id'], ['id']
    )


def downgrade():
    op.drop_table('related_dataset')
    op.drop_table('related')
