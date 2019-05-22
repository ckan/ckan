# encoding: utf-8
"""014 Hash 2

Revision ID: 93519b684820
Revises: 8a3a5af39797
Create Date: 2018-09-04 18:48:52.968191

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '93519b684820'
down_revision = '8a3a5af39797'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column(
        'package_resource_revision', sa.Column('hash', sa.UnicodeText)
    )


def downgrade():
    op.drop_column('package_resource_revision', 'hash')
