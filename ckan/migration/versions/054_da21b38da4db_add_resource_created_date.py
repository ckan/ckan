"""054 Add resource created date

Revision ID: da21b38da4db
Revises: 9d051a099097
Create Date: 2018-09-04 18:49:07.555419

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'da21b38da4db'
down_revision = '9d051a099097'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('resource', sa.Column('created', sa.TIMESTAMP))
    op.add_column('resource_revision', sa.Column('created', sa.TIMESTAMP))


def downgrade():
    op.drop_column('resource', 'created')
    op.drop_column('resource_revision', 'created')
