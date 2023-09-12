"""empty remove tracking if empty tables

Revision ID: 59f3ca9590d9
Revises: 9f33a0280c51
Create Date: 2023-09-12 11:56:52.237821

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59f3ca9590d9'
down_revision = '9f33a0280c51'
branch_labels = None
depends_on = None


def upgrade():
    """Remove tracking tables if they are empty.
    
    Starting CKAN 2.11 tracking has been refactored to its own extension.
    When running the migration from CKAN 2.10 to 2.11, `ckan db init` will 
    run this migration and remove the tables if they are empty. 
    (This assume that the tracking extension was never enabled)
    """
    tracking_rows = sa.sql.select([sa.sql.func.count('*')]).select_from(
        sa.sql.table('tracking_raw')
    )
    rows = op.get_bind().execute(tracking_rows).scalar()
    if rows == 0:
        op.drop_table('tracking_summary')
        op.drop_table('tracking_raw')      


def downgrade():
    op.drop_table('tracking_summary')
    op.drop_table('tracking_raw')
