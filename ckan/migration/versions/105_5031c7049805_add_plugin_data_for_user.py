"""empty message

Revision ID: 5031c7049805
Revises: 9f33a0280c51
Create Date: 2024-05-03 16:30:13.861028

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '5031c7049805'
down_revision = '9f33a0280c51'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        u'user',
        sa.Column(
            u'plugin_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True)
    )


def downgrade():
    op.drop_column(u'user', u'plugin_data')
