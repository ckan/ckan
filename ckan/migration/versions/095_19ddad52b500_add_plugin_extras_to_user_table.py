"""Add plugin_extras to user table

Revision ID: 19ddad52b500
Revises: 588d7cfb9a41
Create Date: 2020-05-12 22:19:37.878470

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '19ddad52b500'
down_revision = u'588d7cfb9a41'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column(
            'plugin_extras',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True)
    )


def downgrade():
    op.drop_column('user', 'plugin_extras')
