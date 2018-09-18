# encoding: utf-8
"""057 Tracking

Revision ID: 660a5aae527e
Revises: 11af3215ae89
Create Date: 2018-09-04 18:49:08.573692

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '660a5aae527e'
down_revision = '11af3215ae89'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
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
