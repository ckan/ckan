"""Create con_package_resource_unique_position constraint
to make resource positions unique per package.

Sets deleted resource positions to null.

Revision ID: e12e991f586b
Revises: f7b64c701a10
Create Date: 2026-02-10 18:26:31.122945

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e12e991f586b'
down_revision = 'f7b64c701a10'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE resource SET position=null WHERE state='deleted';
    """)
    print('Set position=null for deleted resources.')

    op.create_unique_constraint(
        constraint_name='con_package_resource_unique_position',
        table_name='resource', columns=['package_id', 'position'],
        deferrable=True, initially="DEFERRED")
    print('Created "con_package_resource_unique_position"' \
          ' constraint on resource table')


def downgrade():
    op.drop_constraint(
        constraint_name='con_package_resource_unique_position',
        table_name='resource',
        type_='unique')
    print('Dropped "con_package_resource_unique_position"' \
          ' constraint from resource table')
