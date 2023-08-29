# encoding: utf-8

"""create conditinal index on user

Revision ID: ff13667243ed
Revises: d111f446733b
Create Date: 2022-06-22 11:38:27.553446

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff13667243ed'
down_revision = 'd111f446733b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "idx_only_one_active_email", "user", ["email", "state"],
        unique=True, postgresql_where=sa.text('"user".state=\'active\''))


def downgrade():
    op.drop_index("idx_only_one_active_email")
