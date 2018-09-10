"""071 Add state column to_user_table

Revision ID: c16f081ef73a
Revises: cfb544112fa7
Create Date: 2018-09-04 18:49:13.351494

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c16f081ef73a'
down_revision = 'cfb544112fa7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column(
            'state', sa.UnicodeText, nullable=False, server_default='active'
        )
    )


def downgrade():
    op.drop_column('user', 'state')
