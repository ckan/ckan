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

Manual checking
---------------

As a diagnostic tool, you can manually compare the database as created by the
model code and the migrations code::

     # Database created by model
     ckan -c |ckan.ini| db clean
     ckan -c |ckan.ini| db create-from-model
     sudo -u postgres pg_dump -s -f /tmp/model.sql ckan_default

     # Database created by migrations
     ckan -c |ckan.ini| db clean
     ckan -c |ckan.ini| db init
     sudo -u postgres pg_dump -s -f /tmp/migrations.sql ckan_default

     sudo -u postgres diff /tmp/migrations.sql /tmp/model.sql


Troubleshooting
---------------

If you are working on a branch that adds new database migrations and merge the most recent commits from master, you might find the following error when running the tests (or manually upgrading the database)::

            if len(current_heads) > 1:
                raise MultipleHeads(
                    current_heads,
    >               "%s@head" % branch_label if branch_label else "head")
    E           CommandError: Multiple head revisions are present for given argument 'head'; please specify a specific target revision, '<branchname>@head' to narrow to a specific head, or 'heads' for all heads

    ../../local/lib/python2.7/site-packages/alembic/script/revision.py:271: CommandError

This means that your current alembic history has two heads, because a new database migration was also added in master in the meantime. To check which migrations need adjusting, go to the ``ckan/migrations`` folder and run::

    alembic history

You should see a ``branchpoint`` revision and two ``head`` revisions, like in this example::

    d4d9be9189fe -> 588d7cfb9a41 (head), Add metadata_modified filed to Resource
    d4d9be9189fe -> f789f233226e (head), Add package_member_table
    01afcadbd8c0 -> d4d9be9189fe (branchpoint), Remove activity.revision_id
    0ffc0b277141 -> 01afcadbd8c0, resource package_id index
    980dcd44de4b -> 0ffc0b277141, group_extra group_id index
    23c92480926e -> 980dcd44de4b, delete migrate version table

In this case ``d4d9be9189fe`` was the latest common migration, and changes in master introduced ``588d7cfb9a41``, while we had already added ``f789f233226e``.

The easiest fix is to manually set the down revision in our branch migration to the most recent one in master::

    diff --git a/ckan/migration/versions/f789f233226e_add_package_member_table.py b/ckan/migration/versions/f789f233226e_add_package_member_table.py
    index 5628d1350..ade2dd07f 100644
    --- a/ckan/migration/versions/f789f233226e_add_package_member_table.py
    +++ b/ckan/migration/versions/f789f233226e_add_package_member_table.py
    @@ -10,7 +10,7 @@ import sqlalchemy as sa

     # revision identifiers, used by Alembic.
     revision = 'f789f233226e'
    -down_revision = u'd4d9be9189fe'
    +down_revision = u'588d7cfb9a41'
     branch_labels = None
     depends_on = None

This will give us a linear history once again::

    588d7cfb9a41 -> f789f233226e (head), Add package_member_table
    d4d9be9189fe -> 588d7cfb9a41, Add metadata_modified filed to Resource
    01afcadbd8c0 -> d4d9be9189fe, Remove activity.revision_id
    0ffc0b277141 -> 01afcadbd8c0, resource package_id index
    980dcd44de4b -> 0ffc0b277141, group_extra group_id index
    23c92480926e -> 980dcd44de4b, delete migrate version table

In more complex scenarios like two migrations updating the same tables, you can use the `alembic merge <https://alembic.sqlalchemy.org/en/latest/branches.html#merging-branches>`_ command.
