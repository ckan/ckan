# encoding: utf-8
"""026 Authorization group user pk

Revision ID: 3615b25af443
Revises: b581622ad327
Create Date: 2018-09-04 18:48:57.988110

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '3615b25af443'
down_revision = 'b581622ad327'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
