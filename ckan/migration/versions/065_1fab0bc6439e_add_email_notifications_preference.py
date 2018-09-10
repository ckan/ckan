"""065 Add email notifications preference

Revision ID: 1fab0bc6439e
Revises: 4f8becd4919a
Create Date: 2018-09-04 18:49:11.283832

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1fab0bc6439e'
down_revision = '4f8becd4919a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column(
            'activity_streams_email_notifications',
            sa.Boolean,
            server_default='FALSE'
        )
    )


def downgrade():
    op.drop_column('user', 'activity_streams_email_notifications')
