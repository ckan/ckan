# encoding: utf-8
"""017 Add pkg_relationships

Revision ID: 1250b2ff3e36
Revises: 37ada738328e
Create Date: 2018-09-04 18:48:53.963557

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '1250b2ff3e36'
down_revision = '37ada738328e'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.create_table(
        'package_relationship',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column(
            'subject_package_id', sa.UnicodeText, sa.ForeignKey('package.id')
        ),
        sa.Column(
            'object_package_id', sa.UnicodeText, sa.ForeignKey('package.id')
        ), sa.Column('type', sa.UnicodeText),
        sa.Column('comment', sa.UnicodeText),
        sa.Column('revision_id', sa.UnicodeText, sa.ForeignKey('revision.id'))
    )

    op.create_table(
        'package_relationship_revision',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column(
            'subject_package_id', sa.UnicodeText, sa.ForeignKey('package.id')
        ),
        sa.Column(
            'object_package_id', sa.UnicodeText, sa.ForeignKey('package.id')
        ), sa.Column('type', sa.UnicodeText),
        sa.Column('comment', sa.UnicodeText),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.UnicodeText,
            sa.ForeignKey('package_relationship.id')
        )
    )


def downgrade():
    op.drop_table('package_relationship_revision')
    op.drop_table('package_relationship')
