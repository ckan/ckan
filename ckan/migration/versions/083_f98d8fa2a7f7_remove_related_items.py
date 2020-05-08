# encoding: utf-8
"""083 Remove related items

Revision ID: f98d8fa2a7f7
Revises: 8ea886d0ede4
Create Date: 2018-09-04 18:49:17.615242

"""
from __future__ import print_function
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'f98d8fa2a7f7'
down_revision = '8ea886d0ede4'
branch_labels = None
depends_on = None

WARNING = """

WARNING: The 'related' tables were not deleted as they currently contain data.
Once you have archived the existing data or migrated the data to
ckanext-showcase, you can safely delete the 'related' and 'related_dataset'
tables using:

    psql ckan_default -c 'BEGIN; DROP TABLE related_dataset; \\
    DROP TABLE related; COMMIT;'

"""


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    conn = op.get_bind()
    existing = conn.execute("SELECT COUNT(*) FROM related;").fetchone()
    if existing[0] > 0:
        print(WARNING)
        return
    op.drop_table('related_dataset')
    op.drop_table('related')


def downgrade():

    op.create_table(
        'related', sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('type', sa.UnicodeText, nullable=False),
        sa.Column('title', sa.UnicodeText),
        sa.Column('description', sa.UnicodeText),
        sa.Column('image_url',
                  sa.UnicodeText), sa.Column('url', sa.UnicodeText),
        sa.Column('created', sa.TIMESTAMP),
        sa.Column('owner_id', sa.UnicodeText),
        sa.Column(
            'view_count', sa.Integer, nullable=False, server_default='0'
        ),
        sa.Column('featured', sa.Integer, nullable=False, server_default='0')
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
