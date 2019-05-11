# encoding: utf-8
"""006 Add ratings

Revision ID: c83955e7acb6
Revises: 12c2232c15f5
Create Date: 2018-09-04 17:39:11.520922

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'c83955e7acb6'
down_revision = '12c2232c15f5'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.create_table(
        'rating',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('user_id', sa.UnicodeText, sa.ForeignKey('user.id')),
        sa.Column('user_ip_address',
                  sa.UnicodeText),  # alternative to user_id if not logged in
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('rating', sa.Float)
    )


def downgrade():
    op.drop_table('rating')
