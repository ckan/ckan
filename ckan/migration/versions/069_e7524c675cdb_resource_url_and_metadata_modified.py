# encoding: utf-8
"""069 Resource url and metadata_modified

Revision ID: e7524c675cdb
Revises: e33a5f2b2a84
Create Date: 2018-09-04 18:49:12.639912

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'e7524c675cdb'
down_revision = 'e33a5f2b2a84'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.add_column('resource', sa.Column('url_type', sa.UnicodeText))
    op.add_column('resource_revision', sa.Column('url_type', sa.UnicodeText))

    op.add_column('package', sa.Column('metadata_modified', sa.TIMESTAMP))
    op.add_column('package', sa.Column('creator_user_id', sa.UnicodeText))
    op.add_column(
        'package_revision', sa.Column('metadata_modified', sa.TIMESTAMP)
    )
    op.add_column(
        'package_revision', sa.Column('creator_user_id', sa.UnicodeText)
    )


def downgrade():

    op.drop_column('resource', 'url_type')
    op.drop_column('resource_revision', 'url_type')

    op.drop_column('package', 'metadata_modified')
    op.drop_column('package', 'creator_user_id')
    op.drop_column('package_revision', 'metadata_modified')
    op.drop_column('package_revision', 'creator_user_id')
