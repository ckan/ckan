# encoding: utf-8

"""fix conditional index on user

Revision ID: f7b64c701a10
Revises: 4eaa5fcf3092
Create Date: 2025-11-28 17:53:21.400558

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7b64c701a10'
down_revision = '4eaa5fcf3092'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "idx_only_one_active_email_no_case", "user",
        [sa.func.lower(sa.Column('email'))],
        unique=True, postgresql_where=sa.text('"user".state=\'active\''))
    op.drop_index("idx_only_one_active_email")


def downgrade():
    op.drop_index("idx_only_one_active_email_no_case")
    op.create_index(
        "idx_only_one_active_email", "user", ["email", "state"],
        unique=True, postgresql_where=sa.text('"user".state=\'active\''))
