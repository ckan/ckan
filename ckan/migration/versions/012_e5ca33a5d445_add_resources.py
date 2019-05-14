# encoding: utf-8
"""012 Add resources

Revision ID: e5ca33a5d445
Revises: 866f6370b4ac
Create Date: 2018-09-04 18:48:52.303211

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'e5ca33a5d445'
down_revision = '866f6370b4ac'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.create_table(
        'package_resource', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('url', sa.UnicodeText, nullable=False),
        sa.Column('format', sa.UnicodeText),
        sa.Column('description', sa.UnicodeText),
        sa.Column('position', sa.Integer), sa.Column('state_id', sa.Integer),
        sa.Column('revision_id', sa.UnicodeText, sa.ForeignKey('revision.id'))
    )

    op.create_table(
        'package_resource_revision',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('url', sa.UnicodeText, nullable=False),
        sa.Column('format', sa.UnicodeText),
        sa.Column('description', sa.UnicodeText),
        sa.Column('position', sa.Integer), sa.Column('state_id', sa.Integer),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.Integer, sa.ForeignKey('package_resource.id')
        )
    )

    op.drop_column('package', 'download_url')
    op.drop_column('package_revision', 'download_url')


def downgrade():
    op.drop_table('package_resource_revision')
    op.drop_table('package_resource')
    op.add_column(
        'package',
        sa.Column('download_url', sa.UnicodeText()),
    )
    op.add_column(
        'package_revision',
        sa.Column('download_url', sa.UnicodeText()),
    )
