# -*- coding: utf-8 -*-
"""Create ApiToken table

Revision ID: 3ae4b17ed66d
Revises: ddbd0a9a4489
Create Date: 2020-03-26 18:50:47.502458

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3ae4b17ed66d"
down_revision = "ddbd0a9a4489"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_token",
        sa.Column("id", sa.UnicodeText, primary_key=True),
        sa.Column("name", sa.UnicodeText),
        sa.Column("user_id", sa.UnicodeText, sa.ForeignKey("user.id")),
        sa.Column(
            "created_at", sa.DateTime,
            server_default=sa.func.current_timestamp()
        ),
        sa.Column("last_access", sa.DateTime, nullable=True),
        sa.Column(
            "plugin_extras",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        )
    )


def downgrade():
    op.drop_table("api_token")
