"""068 Add package extras index

Revision ID: e33a5f2b2a84
Revises: 266c110eafec
Create Date: 2018-09-04 18:49:12.301432

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e33a5f2b2a84'
down_revision = '266c110eafec'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'idx_package_extra_package_id', 'package_extra_revision',
        ['package_id', 'current']
    )


def downgrade():
    op.drop_index('idx_package_extra_package_id', 'package_extra_revision')
