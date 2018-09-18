# encoding: utf-8
"""064 Add email_last_sent_column

Revision ID: 4f8becd4919a
Revises: 8b633852cb7a
Create Date: 2018-09-04 18:49:10.939639

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '4f8becd4919a'
down_revision = '8b633852cb7a'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column(
        'dashboard',
        sa.Column(
            'email_last_sent',
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.func.localtimestamp()
        )
    )


def downgrade():
    op.drop_column('dashboard', 'email_last_sent')
