"""028 Drop harvest_source_status

Revision ID: cdd68fe9ba21
Revises: 11e5745c6fc9
Create Date: 2018-09-04 18:48:58.674039

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cdd68fe9ba21'
down_revision = '11e5745c6fc9'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('harvest_source', 'status', nullable=False)


def downgrade():
    op.alter_column('harvest_source', 'status', nullable=True)
