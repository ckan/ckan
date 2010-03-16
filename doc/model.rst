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

The current version the database is migrated to is also stored in the database. When you run the upgrade, as each migration script is run it prints to the console something like '11->12'. If no upgrade is required because it is up to date, then nothing is printed.

Creating a new migration script
===============================

A migration script should be checked into CKAN at the same time as not only the model changes it is related to, but also a migration test, to check is all is well.

To create a new migration script, create a python file in ckan/migration/versions/ and name it with a prefix numbered one higher than the previous one and some words describing the change.

The golden rule with writing the script is that you don't import the model, however tempting this is. You must work at a lower level than the object level to manipulate the tables. 

  Reasoning: If you were to import the model, then you would get the new model's ORM which may not relate to the current table structure. Imagine you have a database at model version 10 and migration scripts exist to take it to version 15. During running script 11, importing the model will try and run a model version 15 on a database which is at best at version 11. Note that you may not spot the problem until scripts for 12-15 are written and you need to upgrade 10->15. So don't import the model!

You need to use the special engine provided by the SqlAlchemy Migrate. Here is the standard header for your migrate script::

 from sqlalchemy import *
 from migrate import *
 metadata = MetaData(migrate_engine)

To get a table you need to reflect from the database. e.g.::

 package_table = Table('package', metadata, autoload=True)

Now the migration operations go in the upgrade function::

 def upgrade():

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

If you are creating a revisioned object (vdm feature) then you need to remember to add the revision_id column and related revision table too. See 017_add_pkg_relationships.py for an example.

More complicated migrations require dropping the foreign key constraints. See 016_uuids_everywhere.py for an example of changing primary keys.

Testing Migration Scripts
=========================

It is somewhat difficult to check a migration script does what you want, but the testing framework makes it easy and repeatable.

Only the latest migration test is relevant, because it uses the model as defined in ckan/model when you run the test. So if you have just changed the model, added new migration script 18, then you need to create test_18. Now test_17 is out of date (although v. useful for reference).

First you need to create a testmigrate.ini and create a new database that it refers to::

 sqlalchemy.url = postgres://tester:pass@localhost/ckantestmigrate

Now run the migration test like this::

 nosetests ckan/migration/tests/test_18.py --with-pylons=testmigrate.ini

There are three basic tests that need to be covered:

1. Migration scripts run with empty database.

 This is the same as doing::

  $ paster db clean
  $ paster db upgrade
  $ paster db init

 We need to check this basic pattern doesn't cause exceptions.

2. Test model migrated from scratch

 With the model created in the previous step, does it work as expected?

3. Test model migrated from previous version, populated with existing data

 This requires a dump of data in the database as it was in the previous version. The test runs the migration script on it and you check that it now looks right.

 The dump of previous database might be created using a repository clone that still has the previous model code::

  $ paster db clean
  $ paster db init
  $ paster create-test-data
  $ export PGPASSWORD=pass&&pg_dump -U tester -D ckantest -h localhost > ckan/migration/tests/test_dumps/test_data_17.pg_dump

 (Reminder: the database log-in details are stored in your .ini file)

 Or instead of create-test-data you may use some real data.

Additionally a fourth test might well be useful:

4. Test migration of real data

 The migration tests are setup to allow using a real database. 

 To get hold of the database you will need to run pg_dump on the server (see previous example). There is a simple way to do this using fabric. For example, you might get a copy of ckan.net's data using fabric (you will need priviledges for the OKFN server to do this)::

  $ fab ckan_net backup

 Once you have the dump file locally, you need to refer to it in your testmigrate.ini in the [app:main] section. For example::

  test_migration_db_dump = ~/db_backup/ckan.net/ckan.net.2010-01-13.pg_dump

 Now you can test the migration of this real data in a migration test like this::

  self.paster('db clean')
  self.setup_db()
  self.paster('db upgrade')
  # test examples:
  from ckan import model
  assert model.Package.by_name(u'osm').title == u'Open Street Map'
