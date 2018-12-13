"""
   Module for visitor class mapping.
"""
import sqlalchemy as sa

from migrate.changeset import ansisql
from migrate.changeset.databases import (sqlite,
                                         postgres,
                                         mysql,
                                         oracle,
                                         firebird)


# Map SA dialects to the corresponding Migrate extensions
DIALECTS = {
    "default": ansisql.ANSIDialect,
    "sqlite": sqlite.SQLiteDialect,
    "postgres": postgres.PGDialect,
    "postgresql": postgres.PGDialect,
    "mysql": mysql.MySQLDialect,
    "oracle": oracle.OracleDialect,
    "firebird": firebird.FBDialect,
}


# NOTE(mriedem): We have to conditionally check for DB2 in case ibm_db_sa
# isn't available since ibm_db_sa is not packaged in sqlalchemy like the
# other dialects.
try:
    from migrate.changeset.databases import ibmdb2
    DIALECTS["ibm_db_sa"] = ibmdb2.IBMDBDialect
except ImportError:
    pass


def get_engine_visitor(engine, name):
    """
    Get the visitor implementation for the given database engine.

    :param engine: SQLAlchemy Engine
    :param name: Name of the visitor
    :type name: string
    :type engine: Engine
    :returns: visitor
    """
    # TODO: link to supported visitors
    return get_dialect_visitor(engine.dialect, name)


def get_dialect_visitor(sa_dialect, name):
    """
    Get the visitor implementation for the given dialect.

    Finds the visitor implementation based on the dialect class and
    returns and instance initialized with the given name.

    Binds dialect specific preparer to visitor.
    """

    # map sa dialect to migrate dialect and return visitor
    sa_dialect_name = getattr(sa_dialect, 'name', 'default')
    migrate_dialect_cls = DIALECTS[sa_dialect_name]
    visitor = getattr(migrate_dialect_cls, name)

    # bind preparer
    visitor.preparer = sa_dialect.preparer(sa_dialect)

    return visitor

def run_single_visitor(engine, visitorcallable, element,
    connection=None, **kwargs):
    """Taken from :meth:`sqlalchemy.engine.base.Engine._run_single_visitor`
    with support for migrate visitors.
    """
    if connection is None:
        conn = engine.contextual_connect(close_with_result=False)
    else:
        conn = connection
    visitor = visitorcallable(engine.dialect, conn)
    try:
        if hasattr(element, '__migrate_visit_name__'):
            fn = getattr(visitor, 'visit_' + element.__migrate_visit_name__)
        else:
            fn = getattr(visitor, 'visit_' + element.__visit_name__)
        fn(element, **kwargs)
    finally:
        if connection is None:
            conn.close()
