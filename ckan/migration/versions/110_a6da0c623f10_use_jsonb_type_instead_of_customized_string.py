"""Replace custom JSON type with JSONB column.

Revision ID: a6da0c623f10
Revises: 9445ce34fc23
Create Date: 2026-05-08 13:34:31.431283

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a6da0c623f10"
down_revision = "9445ce34fc23"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "activity",
        "data",
        existing_type=sa.TEXT(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="data::jsonb",
        existing_nullable=True,
    )
    op.alter_column(
        "activity_detail",
        "data",
        existing_type=sa.TEXT(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="data::jsonb",
        existing_nullable=True,
    )
    op.alter_column(
        "resource",
        "extras",
        existing_type=sa.TEXT(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="extras::jsonb",
        existing_nullable=True,
    )
    op.alter_column(
        "resource_view",
        "config",
        existing_type=sa.TEXT(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="config::jsonb",
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "resource_view",
        "config",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    op.alter_column(
        "resource",
        "extras",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    op.alter_column(
        "activity_detail",
        "data",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    op.alter_column(
        "activity",
        "data",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
