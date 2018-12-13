"""
   This module provides an external API to the versioning system.

   .. versionchanged:: 0.6.0
    :func:`migrate.versioning.api.test` and schema diff functions
    changed order of positional arguments so all accept `url` and `repository`
    as first arguments.

   .. versionchanged:: 0.5.4
    ``--preview_sql`` displays source file when using SQL scripts.
    If Python script is used, it runs the action with mocked engine and
    returns captured SQL statements.

   .. versionchanged:: 0.5.4
    Deprecated ``--echo`` parameter in favour of new
    :func:`migrate.versioning.util.construct_engine` behavior.
"""

# Dear migrate developers,
#
# please do not comment this module using sphinx syntax because its
# docstrings are presented as user help and most users cannot
# interpret sphinx annotated ReStructuredText.
#
# Thanks,
# Jan Dittberner

import sys
import inspect
import logging

from migrate import exceptions
from migrate.versioning import (repository, schema, version,
    script as script_) # command name conflict
from migrate.versioning.util import catch_known_errors, with_engine


log = logging.getLogger(__name__)
command_desc = {
    'help': 'displays help on a given command',
    'create': 'create an empty repository at the specified path',
    'script': 'create an empty change Python script',
    'script_sql': 'create empty change SQL scripts for given database',
    'version': 'display the latest version available in a repository',
    'db_version': 'show the current version of the repository under version control',
    'source': 'display the Python code for a particular version in this repository',
    'version_control': 'mark a database as under this repository\'s version control',
    'upgrade': 'upgrade a database to a later version',
    'downgrade': 'downgrade a database to an earlier version',
    'drop_version_control': 'removes version control from a database',
    'manage': 'creates a Python script that runs Migrate with a set of default values',
    'test': 'performs the upgrade and downgrade command on the given database',
    'compare_model_to_db': 'compare MetaData against the current database state',
    'create_model': 'dump the current database as a Python model to stdout',
    'make_update_script_for_model': 'create a script changing the old MetaData to the new (current) MetaData',
    'update_db_from_model': 'modify the database to match the structure of the current MetaData',
}
__all__ = command_desc.keys()

Repository = repository.Repository
ControlledSchema = schema.ControlledSchema
VerNum = version.VerNum
PythonScript = script_.PythonScript
SqlScript = script_.SqlScript


# deprecated
def help(cmd=None, **opts):
    """%prog help COMMAND

    Displays help on a given command.
    """
    if cmd is None:
        raise exceptions.UsageError(None)
    try:
        func = globals()[cmd]
    except:
        raise exceptions.UsageError(
            "'%s' isn't a valid command. Try 'help COMMAND'" % cmd)
    ret = func.__doc__
    if sys.argv[0]:
        ret = ret.replace('%prog', sys.argv[0])
    return ret

@catch_known_errors
def create(repository, name, **opts):
    """%prog create REPOSITORY_PATH NAME [--table=TABLE]

    Create an empty repository at the specified path.

    You can specify the version_table to be used; by default, it is
    'migrate_version'.  This table is created in all version-controlled
    databases.
    """
    repo_path = Repository.create(repository, name, **opts)


@catch_known_errors
def script(description, repository, **opts):
    """%prog script DESCRIPTION REPOSITORY_PATH

    Create an empty change script using the next unused version number
    appended with the given description.

    For instance, manage.py script "Add initial tables" creates:
    repository/versions/001_Add_initial_tables.py
    """
    repo = Repository(repository)
    repo.create_script(description, **opts)


@catch_known_errors
def script_sql(database, description, repository, **opts):
    """%prog script_sql DATABASE DESCRIPTION REPOSITORY_PATH

    Create empty change SQL scripts for given DATABASE, where DATABASE
    is either specific ('postgresql', 'mysql', 'oracle', 'sqlite', etc.)
    or generic ('default').

    For instance, manage.py script_sql postgresql description creates:
    repository/versions/001_description_postgresql_upgrade.sql and
    repository/versions/001_description_postgresql_downgrade.sql
    """
    repo = Repository(repository)
    repo.create_script_sql(database, description, **opts)


def version(repository, **opts):
    """%prog version REPOSITORY_PATH

    Display the latest version available in a repository.
    """
    repo = Repository(repository)
    return repo.latest


@with_engine
def db_version(url, repository, **opts):
    """%prog db_version URL REPOSITORY_PATH

    Show the current version of the repository with the given
    connection string, under version control of the specified
    repository.

    The url should be any valid SQLAlchemy connection string.
    """
    engine = opts.pop('engine')
    schema = ControlledSchema(engine, repository)
    return schema.version


def source(version, dest=None, repository=None, **opts):
    """%prog source VERSION [DESTINATION] --repository=REPOSITORY_PATH

    Display the Python code for a particular version in this
    repository.  Save it to the file at DESTINATION or, if omitted,
    send to stdout.
    """
    if repository is None:
        raise exceptions.UsageError("A repository must be specified")
    repo = Repository(repository)
    ret = repo.version(version).script().source()
    if dest is not None:
        dest = open(dest, 'w')
        dest.write(ret)
        dest.close()
        ret = None
    return ret


def upgrade(url, repository, version=None, **opts):
    """%prog upgrade URL REPOSITORY_PATH [VERSION] [--preview_py|--preview_sql]

    Upgrade a database to a later version.

    This runs the upgrade() function defined in your change scripts.

    By default, the database is updated to the latest available
    version. You may specify a version instead, if you wish.

    You may preview the Python or SQL code to be executed, rather than
    actually executing it, using the appropriate 'preview' option.
    """
    err = "Cannot upgrade a database of version %s to version %s. "\
        "Try 'downgrade' instead."
    return _migrate(url, repository, version, upgrade=True, err=err, **opts)


def downgrade(url, repository, version, **opts):
    """%prog downgrade URL REPOSITORY_PATH VERSION [--preview_py|--preview_sql]

    Downgrade a database to an earlier version.

    This is the reverse of upgrade; this runs the downgrade() function
    defined in your change scripts.

    You may preview the Python or SQL code to be executed, rather than
    actually executing it, using the appropriate 'preview' option.
    """
    err = "Cannot downgrade a database of version %s to version %s. "\
        "Try 'upgrade' instead."
    return _migrate(url, repository, version, upgrade=False, err=err, **opts)

@with_engine
def test(url, repository, **opts):
    """%prog test URL REPOSITORY_PATH [VERSION]

    Performs the upgrade and downgrade option on the given
    database. This is not a real test and may leave the database in a
    bad state. You should therefore better run the test on a copy of
    your database.
    """
    engine = opts.pop('engine')
    repos = Repository(repository)

    # Upgrade
    log.info("Upgrading...")
    script = repos.version(None).script(engine.name, 'upgrade')
    script.run(engine, 1)
    log.info("done")

    log.info("Downgrading...")
    script = repos.version(None).script(engine.name, 'downgrade')
    script.run(engine, -1)
    log.info("done")
    log.info("Success")


@with_engine
def version_control(url, repository, version=None, **opts):
    """%prog version_control URL REPOSITORY_PATH [VERSION]

    Mark a database as under this repository's version control.

    Once a database is under version control, schema changes should
    only be done via change scripts in this repository.

    This creates the table version_table in the database.

    The url should be any valid SQLAlchemy connection string.

    By default, the database begins at version 0 and is assumed to be
    empty.  If the database is not empty, you may specify a version at
    which to begin instead. No attempt is made to verify this
    version's correctness - the database schema is expected to be
    identical to what it would be if the database were created from
    scratch.
    """
    engine = opts.pop('engine')
    ControlledSchema.create(engine, repository, version)


@with_engine
def drop_version_control(url, repository, **opts):
    """%prog drop_version_control URL REPOSITORY_PATH

    Removes version control from a database.
    """
    engine = opts.pop('engine')
    schema = ControlledSchema(engine, repository)
    schema.drop()


def manage(file, **opts):
    """%prog manage FILENAME [VARIABLES...]

    Creates a script that runs Migrate with a set of default values.

    For example::

        %prog manage manage.py --repository=/path/to/repository \
--url=sqlite:///project.db

    would create the script manage.py. The following two commands
    would then have exactly the same results::

        python manage.py version
        %prog version --repository=/path/to/repository
    """
    Repository.create_manage_file(file, **opts)


@with_engine
def compare_model_to_db(url, repository, model, **opts):
    """%prog compare_model_to_db URL REPOSITORY_PATH MODEL

    Compare the current model (assumed to be a module level variable
    of type sqlalchemy.MetaData) against the current database.

    NOTE: This is EXPERIMENTAL.
    """  # TODO: get rid of EXPERIMENTAL label
    engine = opts.pop('engine')
    return ControlledSchema.compare_model_to_db(engine, model, repository)


@with_engine
def create_model(url, repository, **opts):
    """%prog create_model URL REPOSITORY_PATH [DECLERATIVE=True]

    Dump the current database as a Python model to stdout.

    NOTE: This is EXPERIMENTAL.
    """  # TODO: get rid of EXPERIMENTAL label
    engine = opts.pop('engine')
    declarative = opts.get('declarative', False)
    return ControlledSchema.create_model(engine, repository, declarative)


@catch_known_errors
@with_engine
def make_update_script_for_model(url, repository, oldmodel, model, **opts):
    """%prog make_update_script_for_model URL OLDMODEL MODEL REPOSITORY_PATH

    Create a script changing the old Python model to the new (current)
    Python model, sending to stdout.

    NOTE: This is EXPERIMENTAL.
    """  # TODO: get rid of EXPERIMENTAL label
    engine = opts.pop('engine')
    return PythonScript.make_update_script_for_model(
        engine, oldmodel, model, repository, **opts)


@with_engine
def update_db_from_model(url, repository, model, **opts):
    """%prog update_db_from_model URL REPOSITORY_PATH MODEL

    Modify the database to match the structure of the current Python
    model. This also sets the db_version number to the latest in the
    repository.

    NOTE: This is EXPERIMENTAL.
    """  # TODO: get rid of EXPERIMENTAL label
    engine = opts.pop('engine')
    schema = ControlledSchema(engine, repository)
    schema.update_db_from_model(model)

@with_engine
def _migrate(url, repository, version, upgrade, err, **opts):
    engine = opts.pop('engine')
    url = str(engine.url)
    schema = ControlledSchema(engine, repository)
    version = _migrate_version(schema, version, upgrade, err)

    changeset = schema.changeset(version)
    for ver, change in changeset:
        nextver = ver + changeset.step
        log.info('%s -> %s... ', ver, nextver)

        if opts.get('preview_sql'):
            if isinstance(change, PythonScript):
                log.info(change.preview_sql(url, changeset.step, **opts))
            elif isinstance(change, SqlScript):
                log.info(change.source())

        elif opts.get('preview_py'):
            if not isinstance(change, PythonScript):
                raise exceptions.UsageError("Python source can be only displayed"
                    " for python migration files")
            source_ver = max(ver, nextver)
            module = schema.repository.version(source_ver).script().module
            funcname = upgrade and "upgrade" or "downgrade"
            func = getattr(module, funcname)
            log.info(inspect.getsource(func))
        else:
            schema.runchange(ver, change, changeset.step)
            log.info('done')


def _migrate_version(schema, version, upgrade, err):
    if version is None:
        return version
    # Version is specified: ensure we're upgrading in the right direction
    # (current version < target version for upgrading; reverse for down)
    version = VerNum(version)
    cur = schema.version
    if upgrade is not None:
        if upgrade:
            direction = cur <= version
        else:
            direction = cur >= version
        if not direction:
            raise exceptions.KnownError(err % (cur, version))
    return version
