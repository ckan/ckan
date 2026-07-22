"""Create con_package_resource_unique_position constraint
to make resource positions unique per package.

Sets deleted resource positions to null.

Sets active resource positions incase of duplicates and
none zero based indices.

Revision ID: e12e991f586b
Revises: f7b64c701a10
Create Date: 2026-02-10 18:26:31.122945

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e12e991f586b'
down_revision = 'f7b64c701a10'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE resource SET position=null WHERE state='deleted';
    """)

    op.execute("""
        WITH numbered AS (
            SELECT
                id,
                package_id,
                position,
                ROW_NUMBER() OVER (
                    PARTITION BY package_id
                    ORDER BY position
                ) - 1 AS new_position
            FROM resource WHERE state='active'
        )
        UPDATE resource
            SET position=numbered.new_position
            FROM numbered
            WHERE resource.id = numbered.id
            AND resource.position != numbered.new_position;
    """)

    op.create_unique_constraint(
        constraint_name='con_package_resource_unique_position',
        table_name='resource', columns=['package_id', 'position'],
        deferrable=True, initially="DEFERRED")


def downgrade():
    op.drop_constraint(
        constraint_name='con_package_resource_unique_position',
        table_name='resource',
        type_='unique')
