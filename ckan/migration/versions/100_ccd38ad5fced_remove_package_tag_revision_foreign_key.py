# encoding: utf-8

"""Remove package_tag_revision foreign key

Revision ID: ccd38ad5fced
Revises: 3ae4b17ed66d
Create Date: 2020-08-13 20:39:03.031606

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "ccd38ad5fced"
down_revision = "3ae4b17ed66d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "package_tag_revision_continuity_id_fkey",
        "package_tag_revision",
        type_="foreignkey",
    )
    op.drop_constraint(
        "package_tag_revision_package_id_fkey",
        "package_tag_revision",
        type_="foreignkey",
    )
    op.drop_constraint(
        "package_extra_revision_package_id_fkey",
        "package_extra_revision",
        type_="foreignkey",
    )
    op.drop_constraint(
        "group_revision_continuity_id_fkey",
        "group_revision",
        type_="foreignkey",
    )
    op.drop_constraint(
        "member_revision_group_id_fkey",
        "member_revision",
        type_="foreignkey",
    )


def downgrade():
    op.create_foreign_key(
        "package_tag_revision_continuity_id_fkey",
        "package_tag_revision",
        "package_tag",
        ["continuity_id"],
        ["id"],
    )
    op.create_foreign_key(
        "package_tag_revision_package_id_fkey",
        "package_tag_revision",
        "package",
        ["package_id"],
        ["id"],
    )
    op.create_foreign_key(
        "package_extra_revision_package_id_fkey",
        "package_extra_revision",
        "package",
        ["package_id"],
        ["id"],
    )
    op.create_foreign_key(
        "group_revision_continuity_id_fkey",
        "group_revision",
        "group",
        ["continuity_id"],
        ["id"],
    )
    op.create_foreign_key(
        "member_revision_group_id_fkey",
        "member_revision",
        "group",
        ["group_id"],
        ["id"],
    )
