# encoding: utf-8

from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
# from logging.config import fileConfig
from ckan.model import init_model
from ckan.model.meta import metadata
from ckan.plugins import plugin_loaded

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
    FIXME: A number of revision tables/indexes exist only in migrations.

    Ignore for now but remove these exceptions once a migration is created
    to delete them properly or create them in the models as well.
    """
    if type_ == 'table':
        if name.endswith('_alembic_version'):
            # keep migration information from extensions
            return False

        # tracking and activity tables were created in a core migration
        if not plugin_loaded('tracking') and name in (
                'tracking_raw', 'tracking_summary'):
            return False
        if not plugin_loaded('activity') and name in (
                'activity', 'activity_detail'):
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
