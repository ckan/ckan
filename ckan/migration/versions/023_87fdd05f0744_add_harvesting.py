# encoding: utf-8
"""023 Add harvesting

Revision ID: 87fdd05f0744
Revises: 7b324ca6c0dc
Create Date: 2018-09-04 18:48:56.975156

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '87fdd05f0744'
down_revision = '7b324ca6c0dc'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'harvest_source',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('status', sa.UnicodeText, server_default=u'New'),
        sa.Column('url', sa.UnicodeText, unique=True, nullable=False),
        sa.Column('description', sa.UnicodeText, default=u''),
        sa.Column('user_ref', sa.UnicodeText, default=u''),
        sa.Column('publisher_ref', sa.UnicodeText, default=u''),
        sa.Column(
            'created', sa.DateTime, server_default=sa.func.current_timestamp()
        ),
    )

    op.create_table(
        'harvesting_job',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('status', sa.UnicodeText, default=u'', nullable=False),
        sa.Column(
            'created', sa.DateTime, server_default=sa.func.current_timestamp()
        ),
        sa.Column('user_ref', sa.UnicodeText, nullable=False),
        sa.Column('report', sa.UnicodeText, default=u''),
        sa.Column(
            'source_id', sa.UnicodeText, sa.ForeignKey('harvest_source.id')
        ),
    )


def downgrade():
    op.drop_table('harvesting_job')
    op.drop_table('harvest_source')
