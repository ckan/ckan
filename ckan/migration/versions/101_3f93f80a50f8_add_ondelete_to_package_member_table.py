# encoding: utf-8

"""Add ondelete to package_member table

Revision ID: 3f93f80a50f8
Revises: ccd38ad5fced
Create Date: 2020-10-03 15:45:21.942192

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = u'3f93f80a50f8'
down_revision = u'ccd38ad5fced'
branch_labels = None
depends_on = None


def upgrade():
    _drop_fk_constraints()

    op.create_foreign_key(
        u'package_member_user_id_fkey',
        u'package_member',
        u'user', ['user_id'], ['id'],
        ondelete=u'CASCADE'
    )
    op.create_foreign_key(
        u'package_member_package_id_fkey',
        u'package_member',
        u'package', ['package_id'], ['id'],
        ondelete=u'CASCADE'
    )


def downgrade():
    _drop_fk_constraints()

    op.create_foreign_key(
        u'package_member_user_id_fkey',
        u'package_member',
        u'user', ['user_id'], ['id']
    )
    op.create_foreign_key(
        u'package_member_package_id_fkey',
        u'package_member',
        u'package', ['package_id'], ['id']
    )


def _drop_fk_constraints():
    op.drop_constraint(
        u"package_member_user_id_fkey",
        u"package_member",
        type_=u"foreignkey",
    )
    op.drop_constraint(
        u"package_member_package_id_fkey",
        u"package_member",
        type_=u"foreignkey",
    )
