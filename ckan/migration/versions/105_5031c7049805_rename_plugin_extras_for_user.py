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
    op.alter_column(
        u'user',
        'plugin_extras',
        new_column_name='plugin_data',
    )


def downgrade():
    op.alter_column(
        u'user',
        'plugin_data',
        new_column_name='plugin_extras',
    )
