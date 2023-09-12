"""empty message

Revision ID: 496f3b451b52
Revises: 
Create Date: 2023-09-12 12:08:51.835952

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '496f3b451b52'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add tracking tables.
    
    Starting CKAN 2.11 tracking has been refactored to its own extension.
    This migration will create the tracking tables if they don't already
    exist.
    
    When upgragind from 2.10 to 2.11 tables will exist so this migration
    will be skipped.
    """
    has_table = op.get_bind().execute(
        sa.sql.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE "
            "table_schema = 'public' AND table_name = 'tracking_raw')"
        )
    ).scalar()
    if has_table:
        print('Tracking tables already exist, skipping migration.')
        return
    op.create_table(
        'tracking_raw', sa.Column('user_key', sa.String(100), nullable=False),
        sa.Column('url', sa.UnicodeText, nullable=False),
        sa.Column('tracking_type', sa.String(10), nullable=False),
        sa.Column(
            'access_timestamp',
            sa.TIMESTAMP,
            server_default=sa.func.current_timestamp()
        )
    )
    op.create_index('tracking_raw_url', 'tracking_raw', ['url'])
    op.create_index('tracking_raw_user_key', 'tracking_raw', ['user_key'])
    op.create_index(
        'tracking_raw_access_timestamp', 'tracking_raw', ['access_timestamp']
    )

    op.create_table(
        'tracking_summary', sa.Column('url', sa.UnicodeText, nullable=False),
        sa.Column('package_id', sa.UnicodeText),
        sa.Column('tracking_type', sa.String(10), nullable=False),
        sa.Column('count', sa.Integer, nullable=False),
        sa.Column(
            'running_total', sa.Integer, nullable=False, server_default='0'
        ),
        sa.Column(
            'recent_views', sa.Integer, nullable=False, server_default='0'
        ), sa.Column('tracking_date', sa.Date)
    )

    op.create_index('tracking_summary_url', 'tracking_summary', ['url'])
    op.create_index(
        'tracking_summary_package_id', 'tracking_summary', ['package_id']
    )
    op.create_index(
        'tracking_summary_date', 'tracking_summary', ['tracking_date']
    )


def downgrade():
    op.drop_table('tracking_summary')
    op.drop_table('tracking_raw')
