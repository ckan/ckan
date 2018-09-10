"""063 Org changes

Revision ID: 8b633852cb7a
Revises: 6deb2bbab394
Create Date: 2018-09-04 18:49:10.608831

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8b633852cb7a'
down_revision = '6deb2bbab394'
branch_labels = None
depends_on = None


def upgrade():

    op.add_column(
        'user', sa.Column('sysadmin', sa.Boolean, server_default='FALSE')
    )
    op.add_column('package', sa.Column('owner_org', sa.UnicodeText))
    op.add_column(
        'package', sa.Column('private', sa.Boolean, server_default='FALSE')
    )

    op.add_column('package_revision', sa.Column('owner_org', sa.UnicodeText))
    op.add_column(
        'package_revision',
        sa.Column('private', sa.Boolean, server_default='FALSE')
    )

    op.add_column(
        'group',
        sa.Column('is_organization', sa.Boolean, server_default='FALSE')
    )
    op.add_column(
        'group_revision',
        sa.Column('is_organization', sa.Boolean, server_default='FALSE')
    )


def downgrade():

    op.drop_column('user', 'sysadmin')
    op.drop_column('package', 'owner_org')
    op.drop_column('package', 'private')

    op.drop_column('package_revision', 'owner_org')
    op.drop_column('package_revision', 'private')

    op.drop_column('group', 'is_organization')
    op.drop_column('group_revision', 'is_organization')
