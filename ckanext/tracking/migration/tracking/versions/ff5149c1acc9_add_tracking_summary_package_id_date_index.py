"""Add a (package_id, tracking_date) index to tracking_summary

TrackingSummary.get_for_package() filters on package_id and orders by
tracking_date descending. With only single-column indexes, PostgreSQL walks
tracking_summary_date backwards and filters as it goes, which reads the whole
table for a dataset that has no tracking rows yet, such as every newly created
one (#9538).

Revision ID: ff5149c1acc9
Revises: 6313f7679d5f
Create Date: 2026-09-17 09:25:27.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff5149c1acc9'
down_revision = '6313f7679d5f'
branch_labels = None
depends_on = None

INDEX_NAME = 'tracking_summary_package_id_date'


def upgrade():
    # CONCURRENTLY keeps the table writable while the index builds, which can
    # take a while on a large table, and cannot run inside a transaction.
    # IF NOT EXISTS lets sites that already created this index by hand upgrade.
    with op.get_context().autocommit_block():
        op.create_index(
            INDEX_NAME,
            'tracking_summary',
            ['package_id', sa.text('tracking_date DESC')],
            if_not_exists=True,
            postgresql_concurrently=True,
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index(
            INDEX_NAME,
            table_name='tracking_summary',
            if_exists=True,
            postgresql_concurrently=True,
        )
