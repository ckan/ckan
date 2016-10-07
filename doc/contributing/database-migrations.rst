===================
Database migrations
===================

When changes are made to the model classes in ``ckan.model`` that alter CKAN's
database schema, a migration script has to be added to migrate old CKAN
databases to the new database schema when they upgrade their copies of CKAN.
These migration scripts are kept in ``ckan.migration.versions``.

When you upgrade a CKAN instance, as part of the upgrade process you run any
necessary migration scripts with the :ref:`paster db upgrade <db upgrade>`
command.

A migration script should be checked into CKAN at the same time as the model
changes it is related to. Before pushing the changes, ensure the tests pass
when running against the migrated model, which requires the
``--ckan-migration`` setting.

To create a new migration script, create a python file in
``ckan/migration/versions/`` and name it with a prefix numbered one higher than
the previous one and some words describing the change.

You need to use the special engine provided by the SqlAlchemy Migrate. Here is
the standard header for your migrate script: ::

  from sqlalchemy import *
  from migrate import *

The migration operations go in the upgrade function: ::

  def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

The following process should be followed when doing a migration.  This process
is here to make the process easier and to validate if any mistakes have been
made:

1. Get a dump of the database schema before you add your new migrate scripts. ::

     paster --plugin=ckan db clean --config={.ini file}
     paster --plugin=ckan db upgrade --config={.ini file}
     pg_dump -h host -s -f old.sql dbname

2. Get a dump of the database as you have specified it in the model. ::

     paster --plugin=ckan db clean --config={.ini file}

     #this makes the database as defined in the model
     paster --plugin=ckan db create-from-model -config={.ini file}
     pg_dump -h host -s -f new.sql dbname

3. Get agpdiff (apt-get it). It produces sql it thinks that you need to run on
   the database in order to get it to the updated schema. ::

     apgdiff old.sql new.sql > upgrade.diff

(or if you don't want to install java use http://apgdiff.startnet.biz/diff_online.php)

4. The upgrade.diff file created will have all the changes needed in sql.
   Delete the drop index lines as they are not created in the model.

5. Put the resulting sql in your migrate script, e.g. ::

     migrate_engine.execute('''update table .........; update table ....''')

6. Do a dump again, then a diff again to see if the the only thing left are drop index statements.

7. run nosetests with ``--ckan-migration`` flag.

It's that simple.  Well almost.

*  If you are doing any table/field renaming adding that to your new migrate
   script first and use this as a base for your diff (i.e add a migrate script
   with these renaming before 1). This way the resulting sql won't try to drop and
   recreate the field/table!

*  It sometimes drops the foreign key constraints in the wrong order causing an
   error so you may need to rearrange the order in the resulting upgrade.diff.

*  If you need to do any data transfer in the migrations then do it between the
   dropping of the constraints and adding of new ones.

*  May need to add some tests if you are doing data migrations.

An example of a script doing it this way is ``034_resource_group_table.py``.
This script copies the definitions of the original tables in order to do the
renaming the tables/fields.

In order to do some basic data migration testing extra assertions should be
added to the migration script.  Examples of this can also be found in
``034_resource_group_table.py`` for example.

This statement is run at the top of the migration script to get the count of
rows: ::

  package_count = migrate_engine.execute('''select count(*) from package''').first()[0]

And the following is run after to make sure that row count is the same: ::

  resource_group_after = migrate_engine.execute('''select count(*) from resource_group''').first()[0]
  assert resource_group_after == package_count
