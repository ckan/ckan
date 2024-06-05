# encoding: utf-8

from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
# from logging.config import fileConfig
from ckan.model import init_model
from ckan.model.meta import metadata

# When auto-generating migration scripts, uncomment these lines to include in
# the model the revision tables - otherwise Alembic wants to delete them
# from ckan.migration.revision_legacy_code import RevisionTableMappings
# RevisionTableMappings.instance()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_name(name, type_, parent_names):
    """
    FIXME: A number of package, member, revision, tracking and activity-related
    tables/indexes exist only in migrations.

    Ignore for now but remove these exceptions once a migration is created
    to delete them properly or create them in the models as well.
    """
    table = ''
    if type_ == 'index':
        table = parent_names.get('table_name', '')
        # FIXME: indexes not yet reflected in models
        if (name, table) in (
                ('idx_activity_object_id', 'activity'),
                ('idx_activity_user_id', 'activity'),
                ('idx_activity_detail_activity_id', 'activity_detail'),
                ('idx_group_id', 'group'),
                ('idx_group_name', 'group'),
                ('idx_group_extra_group_id', 'group_extra'),
                ('idx_extra_grp_id_pkg_id', 'member'),
                ('idx_group_pkg_id', 'member'),
                ('idx_package_group_group_id', 'member'),
                ('idx_package_group_id', 'member'),
                ('idx_package_group_pkg_id', 'member'),
                ('idx_package_group_pkg_id_group_id', 'member'),
                ('idx_package_creator_user_id', 'package'),
                ('idx_pkg_id', 'package'),
                ('idx_pkg_name', 'package'),
                ('idx_pkg_sid', 'package'),
                ('idx_pkg_sname', 'package'),
                ('idx_pkg_stitle', 'package'),
                ('idx_pkg_title', 'package'),
                ('idx_extra_id_pkg_id', 'package_extra'),
                ('idx_extra_pkg_id', 'package_extra'),
                ('idx_package_tag_id', 'package_tag'),
                ('idx_package_tag_pkg_id', 'package_tag'),
                ('idx_package_tag_pkg_id_tag_id', 'package_tag'),
                ('idx_package_tag_tag_id', 'package_tag'),
                ('idx_tag_id', 'tag'),
                ('idx_tag_name', 'tag'),
                ('term', 'term_translation'),
                ('term_lang', 'term_translation'),
                ('idx_package_resource_id', 'resource'),
                ('idx_package_resource_package_id', 'resource'),
                ('idx_package_resource_url', 'resource'),
                ('idx_view_resource_id', 'resource_view'),
                ('idx_only_one_active_email', 'user'),
                ('idx_user_id', 'user'),
                ('idx_user_name', 'user'),
                ):
            return False

    if type_ == 'table':
        table = name

    # FIXME: everything revision, tracking and rating-related not reflected
    if table == 'revision' or table.endswith('_revision'):
        return False
    if table in ('tracking_raw', 'tracking_summary'):
        return False
    if table == 'rating':
        return False

    if table.endswith('_alembic_version'):
        # keep migration information from extensions
        return False
    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option(u"sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix=u'sqlalchemy.',
        poolclass=pool.NullPool
    )
    connection = connectable.connect()
    init_model(connectable)

    context.configure(
        connection=connection, target_metadata=target_metadata,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
