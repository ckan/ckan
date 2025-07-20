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
down_revision = "4eaa5fcf3092"
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
            "ctime",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("mtime", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("atime", postgresql.TIMESTAMP(timezone=True)),
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
    )

    op.create_table(
        "file_part",
        sa.Column("id", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("name", sa.TEXT(), nullable=False),
        sa.Column("storage", sa.TEXT(), nullable=False),
        sa.Column("location", sa.TEXT(), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "size", sa.BIGINT(), server_default=sa.text("'0'::bigint"), nullable=False
        ),
        sa.Column(
            "content_type", sa.TEXT(), server_default=sa.text("''"), nullable=False
        ),
        sa.Column("hash", sa.TEXT(), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "ctime",
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
    )

    op.create_table(
        "owner",
        sa.Column("item_id", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("item_type", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("owner_id", sa.TEXT(), nullable=False),
        sa.Column("owner_type", sa.TEXT(), nullable=False),
        sa.Column(
            "pinned", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False
        ),
    )

    op.create_table(
        "owner_transfer_history",
        sa.Column("id", sa.TEXT(), nullable=False, primary_key=True),
        sa.Column("item_id", sa.TEXT(), nullable=False),
        sa.Column("item_type", sa.TEXT(), nullable=False),
        sa.Column("owner_id", sa.TEXT(), nullable=False),
        sa.Column("owner_type", sa.TEXT(), nullable=False),
        sa.Column(
            "leave_date",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.TEXT(), nullable=False),
        sa.Index("idx_file_transfer_item", "item_id", "item_type"),
        sa.ForeignKeyConstraint(
            ["item_id", "item_type"],
            ["owner.item_id", "owner.item_type"],
            ondelete="CASCADE",
        ),
    )


def downgrade():
    op.drop_table("owner_transfer_history")
    op.drop_table("owner")
    op.drop_table("file_part")
    op.drop_table("file")
