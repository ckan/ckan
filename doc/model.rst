=====
Model
=====

The structure of the CKAN data is described in the 'model'. This is in the code at::

 ckan/model

Many of the domain objects are Revisioned and some are Stateful. These are concepts introduced by vdm.

Migration
=========

When edits are made to the model code, then before the code can be used on a CKAN instance with existing data, the existing data has to be migrated. This is achieved with a migration script. CKAN currently uses `SqlAlchemy Migrate <http://code.google.com/p/sqlalchemy-migrate/>`_ to manage these scripts.

When you deploy new code to a CKAN instance, as part of the process you run any required migration scripts with::

 paster db upgrade

The scripts give their model version numbers in their filenames and are stored here::

 ckan/migration/versions/ 

The current version the database is migrated to is also stored in the database. When you run the upgrade, as each migration script is run it prints to the console something like ``11->12``. If no upgrade is required because it is up to date, then nothing is printed.

Creating a new migration script
===============================

A migration script should be checked into CKAN at the same time as the model changes it is related to. Before pushing the changes, ensure the tests pass when running against the migrated model, which requires the ``--ckan-migrate`` setting - see `<README.html#migrationtesting>`_.

To create a new migration script, create a python file in ckan/migration/versions/ and name it with a prefix numbered one higher than the previous one and some words describing the change.

The golden rule with writing the script is that you don't import the model, however tempting this is. You must work at a lower level than the object level to manipulate the tables. 

  Reasoning: If you were to import the model, then you would get the new model's ORM which may not relate to the current table structure. Imagine you have a database at model version 10 and migration scripts exist to take it to version 15. During running script 11, importing the model will try and run a model version 15 on a database which is at best at version 11. Note that you may not spot the problem until scripts for 12-15 are written and you need to upgrade 10->15. So don't import the model!

You need to use the special engine provided by the SqlAlchemy Migrate. Here is the standard header for your migrate script::

 from sqlalchemy import *
 from migrate import *


The migration operations go in the upgrade function::

 def upgrade(migrate_engine):
     metadata = MetaData()
     metadata.bind = migrate_engine

To get a table you need to reflect from the database. e.g.::

     package_table = Table('package', metadata, autoload=True)

See the `SqlAlchemy Migrate documentation <http://packages.python.org/sqlalchemy-migrate/>`_ for full operations. You might add a new table::

     package_relationship_table = Table('package_relationship', metadata,
         Column('id', UnicodeText, primary_key=True),
         Column('subject_package_id', UnicodeText, ForeignKey('package.id')),
         Column('object_package_id', UnicodeText, ForeignKey('package.id')),
         Column('type', UnicodeText),
         Column('comment', UnicodeText),
         )
     package_relationship_table.create()

Or add a column to an existing table like this::

     column = Column('author', UnicodeText)
     column.create(package)

(Note: To add 'create' and other useful migration methods to the SqlAlchemy objects you will have to also import migrate.changeset)

If you are creating a revisioned object (vdm feature) then you need to remember to add the revision_id column and related revision table too. See 017_add_pkg_relationships.py for an example.

More complicated migrations require dropping the foreign key constraints. See 016_uuids_everywhere.py for an example of changing primary keys.
