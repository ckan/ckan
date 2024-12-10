"""Migration scripts for tracking

Revision ID: 6313f7679d5f
Revises:
Create Date: 2024-10-11 19:21:29.449298

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '6313f7679d5f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # add composite primary key
    op.create_primary_key(
        'tracking_raw_pkey', 'tracking_raw', ['user_key', 'url', 'access_timestamp']
    )


def downgrade():
    op.drop_constraint('tracking_raw_pkey', 'tracking_raw')
