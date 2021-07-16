# encoding: utf-8

"""Remove activity.revision_id

Revision ID: d4d9be9189fe
Revises: 01afcadbd8c0
Create Date: 2019-11-01 16:33:28.320542

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4d9be9189fe'
down_revision = '01afcadbd8c0'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('group_revision_id_fkey', 'group',
                       type_='foreignkey')
    op.drop_column('group', 'revision_id')
    op.drop_constraint('group_extra_revision_id_fkey', 'group_extra',
                       type_='foreignkey')
    op.drop_column('group_extra', 'revision_id')
    op.drop_constraint('member_revision_id_fkey', 'member',
                       type_='foreignkey')
    op.drop_column('member', 'revision_id')
    op.drop_constraint('package_revision_id_fkey', 'package',
                       type_='foreignkey')
    op.drop_column('package', 'revision_id')
    op.drop_constraint('package_extra_revision_id_fkey', 'package_extra',
                       type_='foreignkey')
    op.drop_column('package_extra', 'revision_id')
    op.drop_constraint('package_relationship_revision_id_fkey',
                       'package_relationship', type_='foreignkey')
    op.drop_column('package_relationship', 'revision_id')
    op.drop_constraint('package_tag_revision_id_fkey', 'package_tag',
                       type_='foreignkey')
    op.drop_column('package_tag', 'revision_id')
    op.drop_constraint('resource_revision_id_fkey', 'resource',
                       type_='foreignkey')
    op.drop_column('resource', 'revision_id')
    op.drop_constraint('system_info_revision_id_fkey', 'system_info',
                       type_='foreignkey')
    op.drop_column('system_info', 'revision_id')


def downgrade():
    op.add_column('system_info',
                  sa.Column('revision_id', sa.TEXT(), autoincrement=False,
                            nullable=True))
    op.create_foreign_key('resource_view_resource_id_fkey', 'resource_view',
                          'resource', ['resource_id'], ['id'],
                          onupdate='CASCADE', ondelete='CASCADE')
    op.add_column('resource', sa.Column('revision_id', sa.TEXT(),
                                         autoincrement=False, nullable=True))
    op.create_foreign_key('resource_revision_id_fkey', 'resource',
                          'revision', ['revision_id'], ['id'])
    op.add_column('package_tag', sa.Column('revision_id', sa.TEXT(),
                                            autoincrement=False,
                                            nullable=True))
    op.create_foreign_key('package_tag_revision_id_fkey', 'package_tag',
                          'revision', ['revision_id'], ['id'])
    op.add_column('package_relationship',
                  sa.Column('revision_id', sa.TEXT(), autoincrement=False,
                            nullable=True))
    op.create_foreign_key('package_relationship_revision_id_fkey',
                          'package_relationship', 'revision',
                          ['revision_id'], ['id'])
    op.add_column('package_extra', sa.Column('revision_id', sa.TEXT(),
                                              autoincrement=False,
                                              nullable=True))
    op.create_foreign_key('package_extra_revision_id_fkey', 'package_extra',
                          'revision', ['revision_id'], ['id'])
    op.add_column('package', sa.Column('revision_id', sa.TEXT(),
                                        autoincrement=False, nullable=True))
    op.create_foreign_key('package_revision_id_fkey', 'package', 'revision',
                          ['revision_id'], ['id'])
    op.add_column('member', sa.Column('revision_id', sa.TEXT(),
                                       autoincrement=False, nullable=True))
    op.create_foreign_key('member_revision_id_fkey', 'member', 'revision',
                          ['revision_id'], ['id'])
    op.add_column('group_extra', sa.Column('revision_id', sa.TEXT(),
                                            autoincrement=False,
                                            nullable=True))
    op.create_foreign_key('group_extra_revision_id_fkey', 'group_extra',
                          'revision', ['revision_id'], ['id'])
    op.add_column('group', sa.Column('revision_id', sa.TEXT(),
                                      autoincrement=False, nullable=True))
    op.create_foreign_key('group_revision_id_fkey', 'group', 'revision',
                          ['revision_id'], ['id'])
