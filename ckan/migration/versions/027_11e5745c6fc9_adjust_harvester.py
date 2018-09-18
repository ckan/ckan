# encoding: utf-8
"""027 Adjust harvester

Revision ID: 11e5745c6fc9
Revises: 3615b25af443
Create Date: 2018-09-04 18:48:58.333396

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '11e5745c6fc9'
down_revision = '3615b25af443'
branch_labels = None
depends_on = None

table = 'harvested_document'


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column(table, sa.Column('guid', sa.UnicodeText, server_default=u''))
    op.add_column(
        table,
        sa.Column(
            'source_id', sa.UnicodeText, sa.ForeignKey('harvest_source.id')
        )
    )
    op.add_column(
        table,
        sa.Column('package_id', sa.UnicodeText, sa.ForeignKey('package.id'))
    )
    op.drop_column(table, 'url')


def downgrade():
    op.drop_column(table, 'package_id')
    op.drop_column(table, 'source_id')
    op.drop_column(table, 'guid')
    op.add_column(table, sa.Column('url', sa.UnicodeText, nullable=False))
