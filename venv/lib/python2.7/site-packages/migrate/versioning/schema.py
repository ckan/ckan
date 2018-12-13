"""
   Database schema version management.
"""
import sys
import logging

import six
from sqlalchemy import (Table, Column, MetaData, String, Text, Integer,
    create_engine)
from sqlalchemy.sql import and_
from sqlalchemy import exc as sa_exceptions
from sqlalchemy.sql import bindparam

from migrate import exceptions
from migrate.changeset import SQLA_07
from migrate.versioning import genmodel, schemadiff
from migrate.versioning.repository import Repository
from migrate.versioning.util import load_model
from migrate.versioning.version import VerNum


log = logging.getLogger(__name__)

class ControlledSchema(object):
    """A database under version control"""

    def __init__(self, engine, repository):
        if isinstance(repository, six.string_types):
            repository = Repository(repository)
        self.engine = engine
        self.repository = repository
        self.meta = MetaData(engine)
        self.load()

    def __eq__(self, other):
        """Compare two schemas by repositories and versions"""
        return (self.repository is other.repository \
            and self.version == other.version)

    def load(self):
        """Load controlled schema version info from DB"""
        tname = self.repository.version_table
        try:
            if not hasattr(self, 'table') or self.table is None:
                    self.table = Table(tname, self.meta, autoload=True)

            result = self.engine.execute(self.table.select(
                self.table.c.repository_id == str(self.repository.id)))

            data = list(result)[0]
        except:
            cls, exc, tb = sys.exc_info()
            six.reraise(exceptions.DatabaseNotControlledError,
                        exceptions.DatabaseNotControlledError(str(exc)), tb)

        self.version = data['version']
        return data

    def drop(self):
        """
        Remove version control from a database.
        """
        if SQLA_07:
            try:
                self.table.drop()
            except sa_exceptions.DatabaseError:
                raise exceptions.DatabaseNotControlledError(str(self.table))
        else:
            try:
                self.table.drop()
            except (sa_exceptions.SQLError):
                raise exceptions.DatabaseNotControlledError(str(self.table))

    def changeset(self, version=None):
        """API to Changeset creation.

        Uses self.version for start version and engine.name
        to get database name.
        """
        database = self.engine.name
        start_ver = self.version
        changeset = self.repository.changeset(database, start_ver, version)
        return changeset

    def runchange(self, ver, change, step):
        startver = ver
        endver = ver + step
        # Current database version must be correct! Don't run if corrupt!
        if self.version != startver:
            raise exceptions.InvalidVersionError("%s is not %s" % \
                                                     (self.version, startver))
        # Run the change
        change.run(self.engine, step)

        # Update/refresh database version
        self.update_repository_table(startver, endver)
        self.load()

    def update_repository_table(self, startver, endver):
        """Update version_table with new information"""
        update = self.table.update(and_(self.table.c.version == int(startver),
             self.table.c.repository_id == str(self.repository.id)))
        self.engine.execute(update, version=int(endver))

    def upgrade(self, version=None):
        """
        Upgrade (or downgrade) to a specified version, or latest version.
        """
        changeset = self.changeset(version)
        for ver, change in changeset:
            self.runchange(ver, change, changeset.step)

    def update_db_from_model(self, model):
        """
        Modify the database to match the structure of the current Python model.
        """
        model = load_model(model)

        diff = schemadiff.getDiffOfModelAgainstDatabase(
            model, self.engine, excludeTables=[self.repository.version_table]
            )
        genmodel.ModelGenerator(diff,self.engine).runB2A()

        self.update_repository_table(self.version, int(self.repository.latest))

        self.load()

    @classmethod
    def create(cls, engine, repository, version=None):
        """
        Declare a database to be under a repository's version control.

        :raises: :exc:`DatabaseAlreadyControlledError`
        :returns: :class:`ControlledSchema`
        """
        # Confirm that the version # is valid: positive, integer,
        # exists in repos
        if isinstance(repository, six.string_types):
            repository = Repository(repository)
        version = cls._validate_version(repository, version)
        table = cls._create_table_version(engine, repository, version)
        # TODO: history table
        # Load repository information and return
        return cls(engine, repository)

    @classmethod
    def _validate_version(cls, repository, version):
        """
        Ensures this is a valid version number for this repository.

        :raises: :exc:`InvalidVersionError` if invalid
        :return: valid version number
        """
        if version is None:
            version = 0
        try:
            version = VerNum(version) # raises valueerror
            if version < 0 or version > repository.latest:
                raise ValueError()
        except ValueError:
            raise exceptions.InvalidVersionError(version)
        return version

    @classmethod
    def _create_table_version(cls, engine, repository, version):
        """
        Creates the versioning table in a database.

        :raises: :exc:`DatabaseAlreadyControlledError`
        """
        # Create tables
        tname = repository.version_table
        meta = MetaData(engine)

        table = Table(
            tname, meta,
            Column('repository_id', String(250), primary_key=True),
            Column('repository_path', Text),
            Column('version', Integer), )

        # there can be multiple repositories/schemas in the same db
        if not table.exists():
            table.create()

        # test for existing repository_id
        s = table.select(table.c.repository_id == bindparam("repository_id"))
        result = engine.execute(s, repository_id=repository.id)
        if result.fetchone():
            raise exceptions.DatabaseAlreadyControlledError

        # Insert data
        engine.execute(table.insert().values(
                           repository_id=repository.id,
                           repository_path=repository.path,
                           version=int(version)))
        return table

    @classmethod
    def compare_model_to_db(cls, engine, model, repository):
        """
        Compare the current model against the current database.
        """
        if isinstance(repository, six.string_types):
            repository = Repository(repository)
        model = load_model(model)

        diff = schemadiff.getDiffOfModelAgainstDatabase(
            model, engine, excludeTables=[repository.version_table])
        return diff

    @classmethod
    def create_model(cls, engine, repository, declarative=False):
        """
        Dump the current database as a Python model.
        """
        if isinstance(repository, six.string_types):
            repository = Repository(repository)

        diff = schemadiff.getDiffOfModelAgainstDatabase(
            MetaData(), engine, excludeTables=[repository.version_table]
            )
        return genmodel.ModelGenerator(diff, engine, declarative).genBDefinition()
