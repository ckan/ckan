# encoding: utf-8
"""067 Turn extras to strings

Revision ID: 266c110eafec
Revises: ad16b3bd8cb6
Create Date: 2018-09-04 18:49:11.961287

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '266c110eafec'
down_revision = 'ad16b3bd8cb6'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
