# encoding: utf-8
"""051 Add tag vocabulary

Revision ID: a4fb0d85ced6
Revises: 01a6b058cb7f
Create Date: 2018-09-04 18:49:06.480087

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'a4fb0d85ced6'
down_revision = '01a6b058cb7f'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.drop_constraint('tag_name_key', 'tag')
    op.create_table(
        'vocabulary', sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('name', sa.String(100), nullable=False)
    )

    op.add_column('tag', sa.Column('vocabulary_id', sa.String(100)))
    op.create_primary_key('vocabulary_pkey', 'vocabulary', ['id'])
    op.create_unique_constraint(
        'tag_name_vocabulary_id_key', 'tag', ['name', 'vocabulary_id']
    )
    op.create_foreign_key(
        'tag_vocabulary_id_fkey', 'tag', 'vocabulary', ['vocabulary_id'],
        ['id']
    )
    op.create_unique_constraint('vocabulary_name_key', 'vocabulary', ['name'])


def downgrade():
    op.drop_constraint('tag_name_vocabulary_id_key', 'tag')
    op.drop_constraint('tag_vocabulary_id_fkey', 'tag')

    op.drop_column('tag', 'vocabulary_id')
    op.drop_table('vocabulary')
    op.create_unique_constraint('tag_name_key', 'tag', ['name'])
