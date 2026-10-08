"""Add a (package_id, tracking_date) index to tracking_summary

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
    invalid = op.get_bind().execute(sa.text(
        "SELECT 1 FROM pg_index "
        "WHERE indexrelid = to_regclass(:name) AND NOT indisvalid"
    ), {"name": INDEX_NAME}).scalar()
    with op.get_context().autocommit_block():
        if invalid:
            op.drop_index(
                INDEX_NAME,
                table_name='tracking_summary',
                postgresql_concurrently=True,
            )
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
