# encoding: utf-8
"""Create existing tables

Revision ID: 103676e0a497
Revises:
Create Date: 2018-09-04 16:57:42.622504

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '103676e0a497'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    op.create_table(
        'state',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Unicode(100)),
    )

    op.create_table(
        'revision',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=False)),
        sa.Column('author', sa.Unicode(200)),
        sa.Column('message', sa.UnicodeText()),
        sa.Column('state_id', sa.Integer),
    )

    op.create_table(
        'apikey',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.UnicodeText()),
        sa.Column('key', sa.UnicodeText()),
    )

    op.create_table(
        'license',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Unicode(100)), sa.Column('state_id', sa.Integer)
    )

    op.create_table(
        'package',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Unicode(100), nullable=False, unique=True),
        sa.Column('title', sa.UnicodeText()),
        sa.Column('version', sa.Unicode(100)),
        sa.Column('url', sa.UnicodeText()),
        sa.Column('download_url', sa.UnicodeText()),
        sa.Column('notes', sa.UnicodeText()),
        sa.Column('license_id', sa.Integer, sa.ForeignKey('license.id')),
        sa.Column('state_id', sa.Integer, sa.ForeignKey('state.id')),
        sa.Column('revision_id', sa.Integer, sa.ForeignKey('revision.id')),
    )

    op.create_table(
        'package_revision',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Unicode(100), nullable=False),
        sa.Column('title', sa.UnicodeText()),
        sa.Column('version', sa.Unicode(100)),
        sa.Column('url', sa.UnicodeText()),
        sa.Column('download_url', sa.UnicodeText()),
        sa.Column('notes', sa.UnicodeText()),
        sa.Column('license_id', sa.Integer, sa.ForeignKey('license.id')),
        sa.Column('state_id', sa.Integer, sa.ForeignKey('state.id')),
        sa.Column(
            'revision_id',
            sa.Integer,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column('continuity_id', sa.Integer, sa.ForeignKey('package.id')),
    )

    op.create_table(
        'tag',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Unicode(100), nullable=False, unique=True),
    )

    op.create_table(
        'package_tag',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('tag_id', sa.Integer, sa.ForeignKey('tag.id')),
        sa.Column('state_id', sa.Integer, sa.ForeignKey('state.id')),
        sa.Column('revision_id', sa.Integer, sa.ForeignKey('revision.id')),
    )

    op.create_table(
        'package_tag_revision',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('tag_id', sa.Integer, sa.ForeignKey('tag.id')),
        sa.Column('state_id', sa.Integer, sa.ForeignKey('state.id')),
        sa.Column(
            'revision_id',
            sa.Integer,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.Integer, sa.ForeignKey('package_tag.id')
        ),
    )

    op.create_table(
        'package_extra',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('key', sa.UnicodeText()),
        sa.Column('value', sa.UnicodeText()),
        sa.Column('state_id', sa.Integer, sa.ForeignKey('state.id')),
        sa.Column('revision_id', sa.Integer, sa.ForeignKey('revision.id')),
    )

    op.create_table(
        'package_extra_revision',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('package_id', sa.Integer, sa.ForeignKey('package.id')),
        sa.Column('key', sa.UnicodeText()),
        sa.Column('value', sa.UnicodeText()),
        sa.Column('state_id', sa.Integer, sa.ForeignKey('state.id')),
        sa.Column(
            'revision_id',
            sa.Integer,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.Integer, sa.ForeignKey('package_extra.id')
        ),
    )


def downgrade():
    op.drop_table('package_extra_revision')
    op.drop_table('package_extra')
    op.drop_table('package_tag_revision')
    op.drop_table('package_tag')
    op.drop_table('tag')
    op.drop_table('package_revision')
    op.drop_table('package')
    op.drop_table('license')
    op.drop_table('apikey')
    op.drop_table('revision')
    op.drop_table('state')
