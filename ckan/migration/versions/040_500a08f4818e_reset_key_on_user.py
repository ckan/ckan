"""040 Reset key on user

Revision ID: 500a08f4818e
Revises: cca459c76d45
Create Date: 2018-09-04 18:49:02.701370

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '500a08f4818e'
down_revision = 'cca459c76d45'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('reset_key', sa.UnicodeText))


def downgrade():
    op.drop_column('user', 'reset_key')
