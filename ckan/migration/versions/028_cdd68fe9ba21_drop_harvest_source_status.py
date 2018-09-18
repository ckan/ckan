# encoding: utf-8
"""028 Drop harvest_source_status

Revision ID: cdd68fe9ba21
Revises: 11e5745c6fc9
Create Date: 2018-09-04 18:48:58.674039

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'cdd68fe9ba21'
down_revision = '11e5745c6fc9'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.alter_column('harvest_source', 'status', nullable=False)


def downgrade():
    op.alter_column('harvest_source', 'status', nullable=True)
