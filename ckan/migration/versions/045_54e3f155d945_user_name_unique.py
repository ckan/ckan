"""045 User name unique

Revision ID: 54e3f155d945
Revises: 4190eeeb8d73
Create Date: 2018-09-04 18:49:04.437304

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '54e3f155d945'
down_revision = '4190eeeb8d73'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('user_name_key', 'user', ['name'])


def downgrade():
    op.drop_constraint('user_name_key', 'user')
