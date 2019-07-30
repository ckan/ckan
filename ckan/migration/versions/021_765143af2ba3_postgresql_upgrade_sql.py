# encoding: utf-8
"""021 Postgresql upgrade.sql

Revision ID: 765143af2ba3
Revises: 4a8577e55a02
Create Date: 2018-09-04 18:48:55.958481

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '765143af2ba3'
down_revision = '69a0b0efc609'
branch_labels = None
depends_on = None

indexes = (
    ('idx_extra_pkg_id', 'package_extra', ['package_id']),
    ('idx_extra_id_pkg_id', 'package_extra', ['id', 'package_id']),
    ('idx_group_pkg_id', 'package_group', ['package_id']),
    ('idx_extra_grp_id_pkg_id', 'package_group', ['group_id', 'package_id']),
    ('idx_pkg_id', 'package', ['id']),
    ('idx_pkg_name', 'package', ['name']),
    ('idx_pkg_title', 'package', ['title']),
    ('idx_pkg_lname', 'package', [sa.text('lower(name)')]),
    ('idx_pkg_uname', 'package', [sa.text('upper(name)')]),
    ('idx_pkg_rev_id', 'package', ['revision_id']),
    ('idx_pkg_sid', 'package', ['id', 'state']),
    ('idx_pkg_sname', 'package', ['name', 'state']),
    ('idx_pkg_stitle', 'package', ['title', 'state']),
    ('idx_pkg_slname', 'package', [sa.text('lower(name)'), 'state']),
    ('idx_pkg_suname', 'package', [sa.text('upper(name)'), 'state']),
    ('idx_pkg_srev_id', 'package', ['revision_id', 'state']),
    ('idx_pkg_revision_id', 'package_revision', ['id']),
    ('idx_pkg_revision_name', 'package_revision', ['name']),
    ('idx_pkg_revision_rev_id', 'package_revision', ['revision_id']),
    ('idx_rev_state', 'revision', ['state']),
    ('idx_tag_id', 'tag', ['id']),
    ('idx_tag_name', 'tag', ['name']),
    ('idx_package_tag_id', 'package_tag', ['id']),
    ('idx_package_tag_tag_id', 'package_tag', ['tag_id']),
    ('idx_package_tag_pkg_id', 'package_tag', ['package_id']),
    ('idx_package_tag_pkg_id_tag_id', 'package_tag', ['tag_id', 'package_id']),
    ('idx_package_tag_revision_id', 'package_tag_revision', ['id']),
    ('idx_package_tag_revision_tag_id', 'package_tag_revision', ['tag_id']),
    (
        'idx_package_tag_revision_rev_id', 'package_tag_revision',
        ['revision_id']
    ),
    (
        'idx_package_tag_revision_pkg_id', 'package_tag_revision',
        ['package_id']
    ),
    (
        'idx_package_tag_revision_pkg_id_tag_id', 'package_tag_revision',
        ['tag_id', 'package_id']
    ),
    ('idx_rating_id', 'rating', ['id']),
    ('idx_rating_user_id', 'rating', ['user_id']),
    ('idx_rating_package_id', 'rating', ['package_id']),
    ('idx_user_id', 'user', ['id']),
    ('idx_user_name', 'user', ['name']),
    # ('idx_uor_id', 'user_object_role', ['id']),
    # ('idx_uor_user_id', 'user_object_role', ['user_id']),
    ('idx_uor_context', 'user_object_role', ['context']),
    ('idx_uor_role', 'user_object_role', ['role']),
    ('idx_uor_user_id_role', 'user_object_role', ['user_id', 'role']),
    ('idx_ra_role', 'role_action', ['role']),
    ('idx_ra_action', 'role_action', ['action']),
    ('idx_ra_role_action', 'role_action', ['action', 'role']),
    ('idx_group_id', 'group', ['id']),
    ('idx_group_name', 'group', ['name']),
    ('idx_package_group_id', 'package_group', ['id']),
    ('idx_package_group_group_id', 'package_group', ['group_id']),
    ('idx_package_group_pkg_id', 'package_group', ['package_id']),
    (
        'idx_package_group_pkg_id_group_id', 'package_group',
        ['group_id', 'package_id']
    ),
    ('idx_package_resource_id', 'package_resource', ['id']),
    ('idx_package_resource_url', 'package_resource', ['url']),
    ('idx_package_resource_pkg_id', 'package_resource', ['package_id']),
    (
        'idx_package_resource_pkg_id_resource_id', 'package_resource',
        ['package_id', 'id']
    ),
    (
        'idx_package_resource_rev_id', 'package_resource_revision',
        ['revision_id']
    ),
    ('idx_package_extra_rev_id', 'package_extra_revision', ['revision_id']),
)


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    for name, table, columns in indexes:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _ in indexes:
        op.drop_index(name, table)
