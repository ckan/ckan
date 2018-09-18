# encoding: utf-8
"""Add author and maintainer

Revision ID: 86fdd8c54775
Revises: 103676e0a497
Create Date: 2018-09-04 17:11:59.181744

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '86fdd8c54775'
down_revision = '103676e0a497'
branch_labels = None
depends_on = None

_columns = (
    'author',
    'author_email',
    'maintainer',
    'maintainer_email',
)


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    for column in _columns:
        op.add_column('package', sa.Column(column, sa.UnicodeText))
        op.add_column('package_revision', sa.Column(column, sa.UnicodeText))


def downgrade():
    for column in reversed(_columns):
        op.drop_column('package_revision', column)
        op.drop_column('package', column)
