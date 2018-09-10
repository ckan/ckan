"""010 Add user about

Revision ID: a6f13bf14d0c
Revises: b739a48de5c4
Create Date: 2018-09-04 18:44:53.313230

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a6f13bf14d0c'
down_revision = 'b739a48de5c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('about', sa.Text))


def downgrade():
    op.drop_column('user', 'about')
