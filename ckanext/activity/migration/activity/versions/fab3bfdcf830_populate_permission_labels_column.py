"""Populate permission_labels column

Revision ID: fab3bfdcf830
Revises: 71713a055d5c
Create Date: 2025-04-10 12:55:05.336000

"""

from alembic import op, context


# revision identifiers, used by Alembic.
revision = "fab3bfdcf830"
down_revision = "71713a055d5c"
branch_labels = None
depends_on = None


def upgrade():
    # Set up the default "public" permission_label for dataset related activity
    # records where the permission labels are null.
    # See https://github.com/ckan/ckan/issues/8775
    if context.is_offline_mode():
        execute = context.execute
    else:
        execute = op.execute

    execute(
        """
        UPDATE activity
        SET permission_labels = '{"public"}'
        WHERE (
            activity_type LIKE '% package' AND
            permission_labels IS NULL
        )
        """
    )



def downgrade():
    pass
