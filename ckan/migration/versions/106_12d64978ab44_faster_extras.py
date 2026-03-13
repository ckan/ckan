"""faster-extras

Revision ID: 12d64978ab44
Revises: 4a5e3465beb6
Create Date: 2024-06-17 18:16:48.398099

"""
from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '12d64978ab44'
down_revision = '4a5e3465beb6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('group', sa.Column(
        'extras',
        postgresql.JSONB(astext_type=sa.Text()),
        sa.CheckConstraint(
            """
            jsonb_typeof(extras) = 'object' and
            not jsonb_path_exists(extras, '$.* ? (@.type() <> "string")')
            """,
            name='group_flat_extras',
        ),
        nullable=True,
    ))

    if context.is_offline_mode():
        execute = context.execute
    else:
        execute = op.execute

    execute(
        """
        update "group" set extras = (
            select json_object(
                array_agg(group_extra.key), array_agg(group_extra.value))
            from group_extra
            where "group".id = group_extra.group_id
            and group_extra.state = 'active'
        )
        """
    )
    op.add_column('package', sa.Column(
        'extras',
        postgresql.JSONB(astext_type=sa.Text()),
        sa.CheckConstraint(
            """
            jsonb_typeof(extras) = 'object' and
            not jsonb_path_exists(extras, '$.* ? (@.type() <> "string")')
            """,
            name='package_flat_extras',
        ),
        nullable=True,
    ))
    execute(
        """
        update package set extras = (
            select json_object(
                array_agg(package_extra.key), array_agg(package_extra.value))
            from package_extra
            where package.id = package_extra.package_id
            and package_extra.state = 'active'
        )
        """
    )
    op.drop_index('idx_group_extra_group_id', table_name='group_extra')
    op.drop_table('group_extra')
    op.drop_index('idx_extra_id_pkg_id', table_name='package_extra')
    op.drop_index('idx_extra_pkg_id', table_name='package_extra')
    op.drop_table('package_extra')


def downgrade():

    if context.is_offline_mode():
        execute = context.execute
    else:
        execute = op.execute

    op.create_table(
        'package_extra',
        sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('key', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('value', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('state', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('package_id', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['package_id'], ['package.id'],
                                name='package_extra_package_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='package_extra_pkey')
    )
    # generate UUIDv8 based on package id + key
    execute(
        """
        insert into package_extra(id, key, value, state, package_id)
        select
            uuid_in(overlay(overlay(
            encode(substring(sha256((p.id || j.key)::bytea) for 16), 'hex')
            placing '8' from 13) placing '8' from 17)::cstring),
            j.key,
            j.value,
            'active',
            p.id
        from package p, jsonb_each_text(p.extras) j;
        """
    )
    op.drop_column('package', 'extras')
    op.create_index('idx_extra_pkg_id', 'package_extra', ['package_id'],
                    unique=False)
    op.create_index('idx_extra_id_pkg_id', 'package_extra',
                    ['id', 'package_id'], unique=False)
    op.create_table(
        'group_extra',
        sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('group_id', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('key', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('value', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('state', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['group.id'],
                                name='group_extra_group_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='group_extra_pkey')
    )
    execute(
        """
        insert into group_extra(id, key, value, state, group_id)
        select
            uuid_in(overlay(overlay(
            encode(substring(sha256((g.id || j.key)::bytea) for 16), 'hex')
            placing '8' from 13) placing '8' from 17)::cstring),
            j.key,
            j.value,
            'active',
            g.id
        from "group" g, jsonb_each_text(g.extras) j;
        """
    )
    op.drop_column('group', 'extras')
    op.create_index('idx_group_extra_group_id', 'group_extra', ['group_id'],
                    unique=False)
