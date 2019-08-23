# encoding: utf-8
"""019 Pkg relationships_state

Revision ID: b2eb6f34a638
Revises: 05a0778051ca
Create Date: 2018-09-04 18:48:54.620241

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'b2eb6f34a638'
down_revision = '05a0778051ca'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column('package_relationship', sa.Column('state', sa.UnicodeText))
    op.add_column(
        'package_relationship_revision', sa.Column('state', sa.UnicodeText)
    )


def downgrade():
    op.drop_column('package_relationship', 'state')
    op.drop_column('package_relationship_revision', 'state')
