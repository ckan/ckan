# encoding: utf-8

from typing import Any


def skip_based_on_legacy_engine_version(op: Any, filename: str) -> bool:
    u'''Safe way to update instances sqlalchemy-migrate migrations applied.

    CKAN `db upgrade/init` command is trying to obtain current version
    of sqlalchemy-migrate migrations from database. In that case, we
    are going to compare existing version from DB with alembic
    migration script's prefix in filename which defines corresponding
    version of sqlalchemy-migrate script.  We need this, because
    alembic uses string ids instead of incremental numbers for
    identifying current migration version. If alembic script's version
    is less than version of currently applied sqlalchemy migration,
    than it just marked as applied, but no SQL queries will be
    actually executed. Thus there are no difference between updating
    existing portals and initializing new ones.
    '''
    conf = op.get_context().config
    version = conf.get_main_option(u'sqlalchemy_migrate_version')
    if version:
        return int(version) >= int(filename.split(u'_', 1)[0])
    return False
