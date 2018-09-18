# encoding: utf-8
"""049 Add group approval status

Revision ID: e0c06c2177b5
Revises: 4a7011172b3f
Create Date: 2018-09-04 18:49:05.797861

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'e0c06c2177b5'
down_revision = '4a7011172b3f'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column('group', sa.Column('approval_status', sa.UnicodeText))
    op.add_column(
        'group_revision', sa.Column('approval_status', sa.UnicodeText)
    )


def downgrade():
    op.drop_column('group', 'approval_status')
    op.drop_column('group_revision', 'approval_status')
