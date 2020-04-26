"""drop continuity_id constraints

Revision ID: 9fadda785b07
Revises: 588d7cfb9a41
Create Date: 2020-04-26 22:27:35.761525

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '9fadda785b07'
down_revision = '588d7cfb9a41'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        u'member_revision_continuity_id_fkey', u'member_revision')
    op.drop_constraint(
        u'resource_revision_continuity_id_fkey', u'resource_revision')
    op.drop_constraint(
        u'package_revision_continuity_id_fkey', u'package_revision')


def downgrade():
    op.create_foreign_key(
        'member_revision_continuity_id_fkey', 'member_revision', 'member',
        ['continuity_id'], ['id']
    )
    op.create_foreign_key(
        'resource_revision_continuity_id_fkey', 'resource_revision',
        'resource', ['continuity_id'], ['id']
    )
    op.create_foreign_key(
        'package_revision_continuity_id_fkey', 'package_revision',
        'package', ['continuity_id'], ['id']
    )
