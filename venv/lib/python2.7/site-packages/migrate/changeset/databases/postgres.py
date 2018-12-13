"""
   `PostgreSQL`_ database specific implementations of changeset classes.

   .. _`PostgreSQL`: http://www.postgresql.org/
"""
from migrate.changeset import ansisql

from sqlalchemy.databases import postgresql as sa_base
PGSchemaGenerator = sa_base.PGDDLCompiler


class PGColumnGenerator(PGSchemaGenerator, ansisql.ANSIColumnGenerator):
    """PostgreSQL column generator implementation."""
    pass


class PGColumnDropper(ansisql.ANSIColumnDropper):
    """PostgreSQL column dropper implementation."""
    pass


class PGSchemaChanger(ansisql.ANSISchemaChanger):
    """PostgreSQL schema changer implementation."""
    pass


class PGConstraintGenerator(ansisql.ANSIConstraintGenerator):
    """PostgreSQL constraint generator implementation."""
    pass


class PGConstraintDropper(ansisql.ANSIConstraintDropper):
    """PostgreSQL constaint dropper implementation."""
    pass


class PGDialect(ansisql.ANSIDialect):
    columngenerator = PGColumnGenerator
    columndropper = PGColumnDropper
    schemachanger = PGSchemaChanger
    constraintgenerator = PGConstraintGenerator
    constraintdropper = PGConstraintDropper
