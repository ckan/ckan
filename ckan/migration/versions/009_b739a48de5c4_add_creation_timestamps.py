"""009 Add creation timestamps

Revision ID: b739a48de5c4
Revises: e8283ffb257e
Create Date: 2018-09-04 18:41:15.442929

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b739a48de5c4'
down_revision = 'e8283ffb257e'
branch_labels = None
depends_on = None

domain_obj_names = ['rating', 'group', 'user']


def upgrade():
    for table in domain_obj_names:
        op.add_column(table, sa.Column('created', sa.TIMESTAMP))


def downgrade():
    for table in domain_obj_names:
        op.drop_column(table, 'created')
