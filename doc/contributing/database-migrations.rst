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

To create a new migration script, use Alembic's automatic generator::

     cd ckan/migration
     alembic revision --autogenerate -m "Add account table"

Review the generated file, because it doesn't detect all changes, and things
like name changes are interpreted as a drop and add, so you'll lose data unless
you change that to an 'alter'. For more details see: https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect

Rename the file to include a prefix numbered one higher than the previous one,
like the others in ``ckan/migration/versions/``.

Manual checking
---------------

As a diagnostic tool, you can manually compare the database as created by the
model code and the migrations code::

     # Database created by model
     paster db clean -c test.ini
     paster db create-from-model -c test.ini
     sudo -u postgres pg_dump -s -f /tmp/model.sql ckan_default

     # Database created by migrations
     paster db clean -c test.ini
     paster db init -c test.ini
     sudo -u postgres pg_dump -s -f /tmp/migrations.sql ckan_default

     sudo -u postgres diff /tmp/migrations.sql /tmp/model.sql
