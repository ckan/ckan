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

A migration script should be checked into CKAN at the same time as the model changes it is related to. Before pushing the changes, ensure the tests pass when running against the migrated model, which requires the ``--ckan-migration`` setting - see `<README.html#migrationtesting>`_.

To create a new migration script, create a python file in ckan/migration/versions/ and name it with a prefix numbered one higher than the previous one and some words describing the change.

You need to use the special engine provided by the SqlAlchemy Migrate. Here is the standard header for your migrate script::

 from sqlalchemy import *
 from migrate import *


The migration operations go in the upgrade function::

 def upgrade(migrate_engine):
     metadata = MetaData()
     metadata.bind = migrate_engine

The following process should be followed when doing a migration.  This process is here to make the process easier and to validate if any mistakes have been made.

1. Get a dump of the database schema before you add your new migrate scripts.

   paster db clean
   paster db upgrade
   pg_dump -h host -s -f old.sql dbname

2.  Get a dump of the database as you have specified it in the model.

   paster db clean
   paster db create-test  #this makes the database as defined in the model
   pg_dump -h host -s -f new.sql dbname

3. Get agpdiff (apt-get it).  It produces sql it thinks that you need to run on the database in order to get it to the updated schema.

   apgdiff old.sql new.sql > upgrade.diff
   (or if you don't want to install java use http://apgdiff.startnet.biz/diff_online.php)

4. The upgrade.diff file created will have all the changes needed in sql.  Delete the drop index lines as they are not created in the model.

5. Put the resulting sql in your migrate script.

   eg migrate_engine.execute('''update table .........; update table ....''')

6.  Do a dump again, then a diff again to see if the the only thing left are drop index statements.

7.  run nosetests with --ckan-migration flag.

Its that simple.  Well almost..

*  If you are doing any table/field renaming adding that to your new migrate script first and use this as a base for your diff (i.e add a migrate script with these renaming before 1).  This way the resulting sql wont try and drop and recreate the field/table!!
*  It sometimes drops the foreign key constraints in the wrong order causing an error so you may need to rearrange the order in the resulting upgrade.diff. 
*  If you need to do any data transfer in the migrations then do it between the dropping of the constraints and adding of new ones.
*  May need to add some tests if you are doing data migrations.

An example of a script doing it this way is 034_resource_group_table.py.  This script copies the definitions of the original tables in order to do the renaming the tables/fields.

In order to do some basic data migration testing extra assertions should be added to the migration script.

Examples of this can also be found in 034_resource_group_table.py for example.

This statement is run at the top of the migration script to get the count of rows::

    package_count = migrate_engine.execute('''select count(*) from package''').first()[0]

And the following is run after to make sure that row count is the same::

    resource_group_after = migrate_engine.execute('''select count(*) from resource_group''').first()[0]
    assert resource_group_after == package_count 


