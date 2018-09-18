# encoding: utf-8
"""007 Add system roles

Revision ID: 1928d4af1cda
Revises: c83955e7acb6
Create Date: 2018-09-04 17:42:00.367475

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '1928d4af1cda'
down_revision = 'c83955e7acb6'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'system_role',
        sa.Column(
            'user_object_role_id',
            sa.UnicodeText,
            sa.ForeignKey('user_object_role.id'),
            primary_key=True
        ),
    )


def downgrade():
    op.drop_table('system_role')
