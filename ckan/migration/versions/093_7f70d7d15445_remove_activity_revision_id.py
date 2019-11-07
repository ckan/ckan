# encoding: utf-8

"""Remove activity.revision_id

Revision ID: d4d9be9189fe
Revises: 01afcadbd8c0
Create Date: 2019-11-01 16:33:28.320542

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = u'd4d9be9189fe'
down_revision = u'01afcadbd8c0'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(u'group_revision_id_fkey', u'group',
                       type_=u'foreignkey')
    op.drop_column(u'group', u'revision_id')
    op.drop_constraint(u'group_extra_revision_id_fkey', u'group_extra',
                       type_=u'foreignkey')
    op.drop_column(u'group_extra', u'revision_id')
    op.drop_constraint(u'member_revision_id_fkey', u'member',
                       type_=u'foreignkey')
    op.drop_column(u'member', u'revision_id')
    op.drop_constraint(u'package_revision_id_fkey', u'package',
                       type_=u'foreignkey')
    op.drop_column(u'package', u'revision_id')
    op.drop_constraint(u'package_extra_revision_id_fkey', u'package_extra',
                       type_=u'foreignkey')
    op.drop_column(u'package_extra', u'revision_id')
    op.drop_constraint(u'package_relationship_revision_id_fkey',
                       u'package_relationship', type_=u'foreignkey')
    op.drop_column(u'package_relationship', u'revision_id')
    op.drop_constraint(u'package_tag_revision_id_fkey', u'package_tag',
                       type_=u'foreignkey')
    op.drop_column(u'package_tag', u'revision_id')
    op.drop_constraint(u'resource_revision_id_fkey', u'resource',
                       type_=u'foreignkey')
    op.drop_column(u'resource', u'revision_id')
    op.drop_constraint(u'system_info_revision_id_fkey', u'system_info',
                       type_=u'foreignkey')
    op.drop_column(u'system_info', u'revision_id')


def downgrade():
    op.add_column(u'system_info',
                  sa.Column(u'revision_id', sa.TEXT(), autoincrement=False,
                            nullable=True))
    op.create_foreign_key(u'resource_view_resource_id_fkey', u'resource_view',
                          u'resource', ['resource_id'], ['id'],
                          onupdate=u'CASCADE', ondelete=u'CASCADE')
    op.add_column(u'resource', sa.Column(u'revision_id', sa.TEXT(),
                                         autoincrement=False, nullable=True))
    op.create_foreign_key(u'resource_revision_id_fkey', u'resource',
                          u'revision', [u'revision_id'], ['id'])
    op.add_column(u'package_tag', sa.Column(u'revision_id', sa.TEXT(),
                                            autoincrement=False,
                                            nullable=True))
    op.create_foreign_key(u'package_tag_revision_id_fkey', u'package_tag',
                          u'revision', [u'revision_id'], ['id'])
    op.add_column(u'package_relationship',
                  sa.Column(u'revision_id', sa.TEXT(), autoincrement=False,
                            nullable=True))
    op.create_foreign_key(u'package_relationship_revision_id_fkey',
                          u'package_relationship', u'revision',
                          [u'revision_id'], ['id'])
    op.add_column(u'package_extra', sa.Column(u'revision_id', sa.TEXT(),
                                              autoincrement=False,
                                              nullable=True))
    op.create_foreign_key(u'package_extra_revision_id_fkey', u'package_extra',
                          u'revision', [u'revision_id'], ['id'])
    op.add_column(u'package', sa.Column(u'revision_id', sa.TEXT(),
                                        autoincrement=False, nullable=True))
    op.create_foreign_key(u'package_revision_id_fkey', u'package', u'revision',
                          [u'revision_id'], ['id'])
    op.add_column(u'member', sa.Column(u'revision_id', sa.TEXT(),
                                       autoincrement=False, nullable=True))
    op.create_foreign_key(u'member_revision_id_fkey', u'member', u'revision',
                          [u'revision_id'], ['id'])
    op.add_column(u'group_extra', sa.Column(u'revision_id', sa.TEXT(),
                                            autoincrement=False,
                                            nullable=True))
    op.create_foreign_key(u'group_extra_revision_id_fkey', u'group_extra',
                          u'revision', [u'revision_id'], ['id'])
    op.add_column(u'group', sa.Column(u'revision_id', sa.TEXT(),
                                      autoincrement=False, nullable=True))
    op.create_foreign_key(u'group_revision_id_fkey', u'group', u'revision',
                          [u'revision_id'], ['id'])
