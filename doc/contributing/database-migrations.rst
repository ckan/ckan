===================
Database migrations
===================

.. _db migrations:

When changes are made to the model classes in ``ckan.model`` that alter CKAN's
database schema, a migration script has to be added to migrate old CKAN
databases to the new database schema when they upgrade their copies of CKAN.
These migration scripts are kept in ``ckan.migration.versions``.

When you upgrade a CKAN instance, as part of the upgrade process you
run any necessary migration scripts with the :ref:`ckan db upgrade <db
upgrade>` command.

A migration script should be checked into CKAN at the same time as the model
changes it is related to.

To create a new migration script, use CKAN CLI::

     ckan generate migration -m "Add account table"

Update the generated file, because it doesn't contain any actual
changes, only placeholders for `upgrade` and `downgrade` steps. For
more details see:
https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script

Rename the file to include a prefix numbered one higher than the previous one,
like the others in ``ckan/migration/versions/``.
