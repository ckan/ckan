"""initialize file tables

Revision ID: 9445ce34fc23
Revises: 4eaa5fcf3092
Create Date: 2025-07-18 21:02:53.834202

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9445ce34fc23"
down_revision = "f7b64c701a10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "file",
        sa.Column("id", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("name", sa.TEXT(), nullable=False),
        sa.Column("storage", sa.TEXT(), nullable=False),
        sa.Column("location", sa.TEXT(), nullable=False),
        sa.Column(
            "content_type",
            sa.TEXT(),
            server_default=sa.text("'application/octet-stream'"),
            nullable=False,
        ),
        sa.Column(
            "size", sa.BIGINT(), server_default=sa.text("'0'::bigint"), nullable=False
        ),
        sa.Column("hash", sa.TEXT(), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "created",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "storage_data",
            postgresql.JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "plugin_data",
            postgresql.JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Index("idx_file_location_in_storage", "storage", "location", unique=True),
    )

    op.create_table(
        "owner",
        sa.Column("item_type", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("item_id", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("owner_type", sa.TEXT(), nullable=False),
        sa.Column("owner_id", sa.TEXT(), nullable=False),
        sa.Column(
            "pinned", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
        sa.Index("idx_owner_owner", "owner_type", "owner_id", unique=False),
    )

    op.create_table(
        "owner_transfer_history",
        sa.Column("id", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("item_id", sa.TEXT(), nullable=False),
        sa.Column("item_type", sa.TEXT(), nullable=False),
        sa.Column("owner_id", sa.TEXT(), nullable=False),
        sa.Column("owner_type", sa.TEXT(), nullable=False),
        sa.Column(
            "at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.TEXT(), nullable=False),
        sa.Column("action", sa.TEXT(), nullable=False, server_default="transfer"),
        sa.Index("idx_owner_transfer_item", "item_id", "item_type"),
    )
    op.create_foreign_key(
        "owner_transfer_history_item_id_item_type_fkey",
        "owner_transfer_history",
        "owner",
        ["item_id", "item_type"],
        ["item_id", "item_type"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_table("owner_transfer_history")
    op.drop_table("owner")
    op.drop_table("file")
