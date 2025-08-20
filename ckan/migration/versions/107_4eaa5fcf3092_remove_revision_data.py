"""remove_revision_data

Revision ID: 4eaa5fcf3092
Revises: 12d64978ab44
Create Date: 2024-07-03 18:46:52.527470

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4eaa5fcf3092"
down_revision = "12d64978ab44"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index(
        "idx_package_relationship_current",
        table_name="package_relationship_revision",
    )
    op.drop_index(
        "idx_period_package_relationship",
        table_name="package_relationship_revision",
    )
    op.drop_table("package_relationship_revision")
    op.drop_index("idx_group_extra_current", table_name="group_extra_revision")
    op.drop_index("idx_group_extra_period", table_name="group_extra_revision")
    op.drop_index(
        "idx_group_extra_period_group", table_name="group_extra_revision"
    )
    op.drop_table("group_extra_revision")
    op.drop_table("system_info_revision")
    op.drop_index("idx_package_continuity_id", table_name="package_revision")
    op.drop_index("idx_package_current", table_name="package_revision")
    op.drop_index("idx_package_period", table_name="package_revision")
    op.drop_index("idx_pkg_revision_id", table_name="package_revision")
    op.drop_index("idx_pkg_revision_name", table_name="package_revision")
    op.drop_index("idx_pkg_revision_rev_id", table_name="package_revision")
    op.drop_table("package_revision")
    op.drop_index(
        "idx_package_tag_continuity_id", table_name="package_tag_revision"
    )
    op.drop_index("idx_package_tag_current", table_name="package_tag_revision")
    op.drop_index(
        "idx_package_tag_revision_id", table_name="package_tag_revision"
    )
    op.drop_index(
        "idx_package_tag_revision_pkg_id", table_name="package_tag_revision"
    )
    op.drop_index(
        "idx_package_tag_revision_pkg_id_tag_id",
        table_name="package_tag_revision",
    )
    op.drop_index(
        "idx_package_tag_revision_rev_id", table_name="package_tag_revision"
    )
    op.drop_index(
        "idx_package_tag_revision_tag_id", table_name="package_tag_revision"
    )
    op.drop_index("idx_period_package_tag", table_name="package_tag_revision")
    op.drop_table("package_tag_revision")
    op.drop_index("idx_group_current", table_name="group_revision")
    op.drop_index("idx_group_period", table_name="group_revision")
    op.drop_table("group_revision")
    op.drop_index(
        "idx_package_extra_continuity_id", table_name="package_extra_revision"
    )
    op.drop_index(
        "idx_package_extra_current", table_name="package_extra_revision"
    )
    op.drop_index(
        "idx_package_extra_package_id", table_name="package_extra_revision"
    )
    op.drop_index(
        "idx_package_extra_period", table_name="package_extra_revision"
    )
    op.drop_index(
        "idx_package_extra_period_package", table_name="package_extra_revision"
    )
    op.drop_index(
        "idx_package_extra_rev_id", table_name="package_extra_revision"
    )
    op.drop_table("package_extra_revision")
    op.drop_index(
        "idx_package_resource_rev_id", table_name="resource_revision"
    )
    op.drop_index("idx_resource_continuity_id", table_name="resource_revision")
    op.drop_index("idx_resource_current", table_name="resource_revision")
    op.drop_index("idx_resource_period", table_name="resource_revision")
    op.drop_table("resource_revision")
    op.drop_index("idx_member_continuity_id", table_name="member_revision")
    op.drop_index("idx_package_group_current", table_name="member_revision")
    op.drop_index(
        "idx_package_group_period_package_group", table_name="member_revision"
    )
    op.drop_table("member_revision")
    op.drop_column("activity", "revision_id")
    op.drop_index("idx_rev_state", table_name="revision")
    op.drop_index("idx_revision_author", table_name="revision")
    op.drop_table("revision")


def downgrade():
    op.create_table(
        "revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "author",
            sa.VARCHAR(length=200),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("message", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "approved_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="revision_pkey"),
        postgresql_ignore_search_path=False,
    )
    op.create_index(
        "idx_revision_author", "revision", ["author"], unique=False
    )
    op.create_index("idx_rev_state", "revision", ["state"], unique=False)
    op.add_column(
        "activity",
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
    )
    op.create_table(
        "member_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("table_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("group_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column(
            "table_name", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column("capacity", sa.TEXT(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="member_revision_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="member_revision_pkey"
        ),
    )
    op.create_index(
        "idx_package_group_period_package_group",
        "member_revision",
        ["revision_timestamp", "expired_timestamp", "table_id", "group_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_group_current",
        "member_revision",
        ["current"],
        unique=False,
    )
    op.create_index(
        "idx_member_continuity_id",
        "member_revision",
        ["continuity_id"],
        unique=False,
    )
    op.create_table(
        "resource_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("url", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("format", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "description", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "position", sa.INTEGER(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column("hash", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("extras", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("name", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "resource_type", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("mimetype", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "mimetype_inner", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("size", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column(
            "last_modified",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("cache_url", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "cache_last_updated",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "webstore_url", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "webstore_last_updated",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "created",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("url_type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "package_id",
            sa.TEXT(),
            server_default=sa.text("''::text"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="resource_revision_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="resource_revision_pkey"
        ),
    )
    op.create_index(
        "idx_resource_period",
        "resource_revision",
        ["revision_timestamp", "expired_timestamp", "id"],
        unique=False,
    )
    op.create_index(
        "idx_resource_current", "resource_revision", ["current"], unique=False
    )
    op.create_index(
        "idx_resource_continuity_id",
        "resource_revision",
        ["continuity_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_resource_rev_id",
        "resource_revision",
        ["revision_id"],
        unique=False,
    )
    op.create_table(
        "package_extra_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("key", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("value", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("package_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="package_extra_revision_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="package_extra_revision_pkey"
        ),
    )
    op.create_index(
        "idx_package_extra_rev_id",
        "package_extra_revision",
        ["revision_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_extra_period_package",
        "package_extra_revision",
        ["revision_timestamp", "expired_timestamp", "package_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_extra_period",
        "package_extra_revision",
        ["revision_timestamp", "expired_timestamp", "id"],
        unique=False,
    )
    op.create_index(
        "idx_package_extra_package_id",
        "package_extra_revision",
        ["package_id", "current"],
        unique=False,
    )
    op.create_index(
        "idx_package_extra_current",
        "package_extra_revision",
        ["current"],
        unique=False,
    )
    op.create_index(
        "idx_package_extra_continuity_id",
        "package_extra_revision",
        ["continuity_id"],
        unique=False,
    )
    op.create_table(
        "group_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("name", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("title", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "description", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "created",
            postgresql.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("type", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "approval_status", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("image_url", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "is_organization",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="group_revision_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="group_revision_pkey"
        ),
    )
    op.create_index(
        "idx_group_period",
        "group_revision",
        ["revision_timestamp", "expired_timestamp", "id"],
        unique=False,
    )
    op.create_index(
        "idx_group_current", "group_revision", ["current"], unique=False
    )
    op.create_table(
        "package_tag_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("package_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("tag_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="package_tag_revision_revision_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tag.id"], name="package_tag_revision_tag_id_fkey"
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="package_tag_revision_pkey"
        ),
    )
    op.create_index(
        "idx_period_package_tag",
        "package_tag_revision",
        ["revision_timestamp", "expired_timestamp", "package_id", "tag_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_tag_revision_tag_id",
        "package_tag_revision",
        ["tag_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_tag_revision_rev_id",
        "package_tag_revision",
        ["revision_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_tag_revision_pkg_id_tag_id",
        "package_tag_revision",
        ["tag_id", "package_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_tag_revision_pkg_id",
        "package_tag_revision",
        ["package_id"],
        unique=False,
    )
    op.create_index(
        "idx_package_tag_revision_id",
        "package_tag_revision",
        ["id"],
        unique=False,
    )
    op.create_index(
        "idx_package_tag_current",
        "package_tag_revision",
        ["current"],
        unique=False,
    )
    op.create_index(
        "idx_package_tag_continuity_id",
        "package_tag_revision",
        ["continuity_id"],
        unique=False,
    )
    op.create_table(
        "package_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "name", sa.VARCHAR(length=100), autoincrement=False, nullable=False
        ),
        sa.Column("title", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "version",
            sa.VARCHAR(length=100),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("url", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("notes", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("author", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "author_email", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("maintainer", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "maintainer_email", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("license_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column("type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("owner_org", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "private",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "metadata_modified",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "creator_user_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "metadata_created",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="package_revision_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="package_revision_pkey"
        ),
    )
    op.create_index(
        "idx_pkg_revision_rev_id",
        "package_revision",
        ["revision_id"],
        unique=False,
    )
    op.create_index(
        "idx_pkg_revision_name", "package_revision", ["name"], unique=False
    )
    op.create_index(
        "idx_pkg_revision_id", "package_revision", ["id"], unique=False
    )
    op.create_index(
        "idx_package_period",
        "package_revision",
        ["revision_timestamp", "expired_timestamp", "id"],
        unique=False,
    )
    op.create_index(
        "idx_package_current", "package_revision", ["current"], unique=False
    )
    op.create_index(
        "idx_package_continuity_id",
        "package_revision",
        ["continuity_id"],
        unique=False,
    )
    op.create_table(
        "system_info_revision",
        sa.Column("id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "key", sa.VARCHAR(length=100), autoincrement=False, nullable=False
        ),
        sa.Column("value", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "continuity_id", sa.INTEGER(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "state",
            sa.TEXT(),
            server_default=sa.text("'active'::text"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["continuity_id"],
            ["system_info.id"],
            name="system_info_revision_continuity_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="system_info_revision_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="system_info_revision_pkey"
        ),
    )
    op.create_table(
        "group_extra_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("group_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("key", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("value", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["group.id"],
            name="group_extra_revision_group_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="group_extra_revision_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="group_extra_revision_pkey"
        ),
    )
    op.create_index(
        "idx_group_extra_period_group",
        "group_extra_revision",
        ["revision_timestamp", "expired_timestamp", "group_id"],
        unique=False,
    )
    op.create_index(
        "idx_group_extra_period",
        "group_extra_revision",
        ["revision_timestamp", "expired_timestamp", "id"],
        unique=False,
    )
    op.create_index(
        "idx_group_extra_current",
        "group_extra_revision",
        ["current"],
        unique=False,
    )
    op.create_table(
        "package_relationship_revision",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "subject_package_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "object_package_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("comment", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_id", sa.TEXT(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "continuity_id", sa.TEXT(), autoincrement=False, nullable=True
        ),
        sa.Column("state", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("expired_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "revision_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "expired_timestamp",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("current", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["continuity_id"],
            ["package_relationship.id"],
            name="package_relationship_revision_continuity_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["object_package_id"],
            ["package.id"],
            name="package_relationship_revision_object_package_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["revision.id"],
            name="package_relationship_revision_revision_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["subject_package_id"],
            ["package.id"],
            name="package_relationship_revision_subject_package_id_fkey",
        ),
        sa.PrimaryKeyConstraint(
            "id", "revision_id", name="package_relationship_revision_pkey"
        ),
    )
    op.create_index(
        "idx_period_package_relationship",
        "package_relationship_revision",
        [
            "revision_timestamp",
            "expired_timestamp",
            "object_package_id",
            "subject_package_id",
        ],
        unique=False,
    )
    op.create_index(
        "idx_package_relationship_current",
        "package_relationship_revision",
        ["current"],
        unique=False,
    )
