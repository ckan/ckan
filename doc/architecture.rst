======================
CKAN Code Architecture
======================

This section tries to give some guidelines for writing code that is consistent
with the intended, overall design and architecture of CKAN.


``ckan.model``
--------------

Encapsulate SQLAlchemy in ``ckan.model``
````````````````````````````````````````

Ideally SQLAlchemy should only be used within ``ckan.model`` and not from other
packages such as ``ckan.logic``.  For example instead of using an SQLAlchemy
query from the logic package to retrieve a particular user from the database,
we add a ``get()`` method to ``ckan.model.user.User``::

    @classmethod
    def get(cls, user_id):
        query = ...
        .
        .
        .
        return query.first()

Now we can call this method from the logic package.

Database Migrations
```````````````````

When changes are made to the model classes in ``ckan.model`` that alter CKAN's
database schema, a migration script has to be added to migrate old CKAN
databases to the new database schema when they upgrade their copies of CKAN.
These migration scripts are kept in ``ckan.migration.versions``.

When you upgrade a CKAN instance, as part of the upgrade process you run any
necessary migration scripts with the ``paster db upgrade`` command::

 paster --plugin=ckan db upgrade --config={.ini file}

Creating a new migration script
```````````````````````````````
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

``ckan.logic``
--------------

Auth Functions and ``check_access()``
``````````````

Each action function defined in ``ckan.logic.action`` should use its own
corresponding auth function defined in ``ckan.logic.auth``. Instead of calling
its auth function directly, an action function should go through
``ckan.logic.check_access`` (which is aliased ``_check_access`` in the action
modules) because this allows plugins to override auth functions using the
``IAuthFunctions`` plugin interface. For example::

    def package_show(context, data_dict):
        _check_access('package_show', context, data_dict)

``check_access`` will raise an exception if the user is not authorized, which
the action function should not catch. When this happens the user will be shown
an authorization error in their browser (or will receive one in their response
from the API).


``logic.get_or_bust()``
`````````````

The ``data_dict`` parameter of logic action functions may be user provided, so
required files may be invalid or absent. Naive Code like::

  id = data_dict['id']

may raise a ``KeyError`` and cause CKAN to crash with a 500 Server Error
and no message to explain what went wrong. Instead do::

  id = _get_or_bust(data_dict, "id")

which will raise ``ValidationError`` if ``"id"`` is not in ``data_dict``. The
``ValidationError`` will be caught and the user will get a 400 Bad Request
response and an error message explaining the problem.


Action Functions are Automatically Exposed in the API
`````````````````````````````````````````````````````

**All** publicly visible functions in the
``ckan.logic.action.{create,delete,get,update}`` namespaces will be exposed
through the :doc:`apiv3`.  **This includes functions imported** by those
modules, **as well as any helper functions** defined within those modules.  To
prevent inadvertent exposure of non-action functions through the action api,
care should be taken to:

1. Import modules correctly (see `Imports`_).  For example: ::

     import ckan.lib.search as search

     search.query_for(...)

2. Hide any locally defined helper functions: ::

     def _a_useful_helper_function(x, y, z):
        '''This function is not exposed because it is marked as private```
        return x+y+z

3. Bring imported convenience functions into the module namespace as private
   members: ::

     _get_or_bust = logic.get_or_bust

Action Function Docstrings
``````````````````````````

See :ref:`Action API Docstrings`.

``get_action()``
````````````````

Don't call ``logic.action`` functions directly, instead use ``get_action()``.
This allows plugins to override action functions using the ``IActions`` plugin
interface. For example::

    ckan.logic.get_action('group_activity_list_html')(...)

Instead of ::

    ckan.logic.action.get.group_activity_list_html(...)


``ckan.lib``
------------

Code in ``ckan.lib`` should not access ``ckan.model`` directly, it should go
through the action functions in ``ckan.logic.action`` instead.


Controller & Template Helper Functions
--------------------------------------

``ckan.lib.helpers`` contains helper functions that can be used from
``ckan.controllers`` or from templates. When developing for ckan core, only use
the helper functions found in ``ckan.lib.helpers.__allowed_functions__``.


.. _Testing:

Testing
-------

- Functional tests which test the behaviour of the web user interface, and the
  APIs should be placed within ``ckan/tests/functional``.  These tests can be a
  lot slower to run that unit tests which don't access the database or solr.  So
  try to bear that in mind, and attempt to cover just what is neccessary, leaving
  what can be tested via unit-testing in unit-tests.

- ``nose.tools.assert_in`` and ``nose.tools.assert_not_in`` are only available
  in Python>=2.7.  So import them from ``ckan.tests``, which will provide
  alternatives if they're not available.

- the `mock`_ library can be used to create and interrogate mock objects.

See :doc:`test` for further information on testing in CKAN.

.. _mock: http://pypi.python.org/pypi/mock

Writing Extensions
------------------

Please see :doc:`writing-extensions` for information about writing ckan
extensions, including details on the API available to extensions.

Deprecation
-----------

- Anything that may be used by extensions (see :doc:`writing-extensions`) needs
  to maintain backward compatibility at call-site.  ie - template helper
  functions and functions defined in the plugins toolkit.

- The length of time of deprecation is evaluated on a function-by-function
  basis.  At minimum, a function should be marked as deprecated during a point
  release.

- To mark a helper function, use the ``deprecated`` decorator found in
  ``ckan.lib.maintain`` eg: ::

    
    @deprecated()
    def facet_items(*args, **kwargs):
        """
        DEPRECATED: Use the new facet data structure, and `unselected_facet_items()`
        """
        # rest of function definition.

