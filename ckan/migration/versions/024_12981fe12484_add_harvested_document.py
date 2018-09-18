# encoding: utf-8
"""024 Add harvested_document

Revision ID: 12981fe12484
Revises: 87fdd05f0744
Create Date: 2018-09-04 18:48:57.309349

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '12981fe12484'
down_revision = '87fdd05f0744'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'harvested_document',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('created', sa.DateTime),
        sa.Column('url', sa.UnicodeText, nullable=False),
        sa.Column('content', sa.UnicodeText, nullable=False),
    )


def downgrade():
    op.drop_table('harvested_document')
