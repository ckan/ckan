# encoding: utf-8

"""Remove package_tag_revision foreign key

Revision ID: ccd38ad5fced
Revises: 3ae4b17ed66d
Create Date: 2020-08-13 20:39:03.031606

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = u"ccd38ad5fced"
down_revision = u"3ae4b17ed66d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        u"package_tag_revision_continuity_id_fkey",
        u"package_tag_revision",
        type_=u"foreignkey",
    )
    op.drop_constraint(
        u"package_tag_revision_package_id_fkey",
        u"package_tag_revision",
        type_=u"foreignkey",
    )
    op.drop_constraint(
        u"package_extra_revision_package_id_fkey",
        u"package_extra_revision",
        type_=u"foreignkey",
    )
    op.drop_constraint(
        u"group_revision_continuity_id_fkey",
        u"group_revision",
        type_=u"foreignkey",
    )
    op.drop_constraint(
        u"member_revision_group_id_fkey",
        u"member_revision",
        type_=u"foreignkey",
    )


def downgrade():
    op.create_foreign_key(
        u"package_tag_revision_continuity_id_fkey",
        u"package_tag_revision",
        u"package_tag",
        [u"continuity_id"],
        ["id"],
    )
    op.create_foreign_key(
        u"package_tag_revision_package_id_fkey",
        u"package_tag_revision",
        u"package",
        [u"package_id"],
        ["id"],
    )
    op.create_foreign_key(
        u"package_extra_revision_package_id_fkey",
        u"package_extra_revision",
        u"package",
        [u"package_id"],
        ["id"],
    )
    op.create_foreign_key(
        u"group_revision_continuity_id_fkey",
        u"group_revision",
        u"group",
        [u"continuity_id"],
        ["id"],
    )
    op.create_foreign_key(
        u"member_revision_group_id_fkey",
        u"member_revision",
        u"group",
        [u"group_id"],
        ["id"],
    )
