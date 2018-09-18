# encoding: utf-8
"""055 Update user and activity_detail

Revision ID: 048f7db947bf
Revises: da21b38da4db
Create Date: 2018-09-04 18:49:07.896968

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '048f7db947bf'
down_revision = 'da21b38da4db'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.alter_column('activity_detail', 'activity_id', nullable=True)
    op.alter_column('user', 'name', nullable=False)


def downgrade():
    op.alter_column('activity_detail', 'activity_id', nullable=False)
    op.alter_column('user', 'name', nullable=True)
