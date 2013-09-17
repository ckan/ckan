=====================
CKAN Coding Standards
=====================

This section documents our CKAN-specific coding standards, which are guidelines
for writing code that is consistent with the intended design and architecture
of CKAN.

For more general coding standards, see also:

* :doc:`python-coding-standards`
* :doc:`html-coding-standards`
* :doc:`css-coding-standards`
* :doc:`javascript-coding-standards`


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
See :doc:`migration`.

.. Add a hidden tocree here to silence Sphinx warning about migration.rst not
   being included in any toctree.

.. toctree::
   :hidden:

   migration

Always go through the Action Functions
``````````````````````````````````````

Whenever some code, for example in ``ckan.lib`` or ``ckan.controllers``, wants
to get, create, update or delete an object from CKAN's model it should do so by
calling a function from the ``ckan.logic.action`` package, and *not* by
accessing ``ckan.model`` directly.


Action Functions are Exposed in the API
```````````````````````````````````````

The functions in ``ckan.logic.action`` are exposed to the world as the
:doc:`api`.  The API URL for an action function is automatically generated
from the function name, for example
``ckan.logic.action.create.package_create()`` is exposed at
``/api/action/package_create``. See `Steve Yegge's Google platforms rant
<https://plus.google.com/112678702228711889851/posts/eVeouesvaVX>`_ for some
interesting discussion about APIs.

**All** publicly visible functions in the
``ckan.logic.action.{create,delete,get,update}`` namespaces will be exposed
through the :doc:`api`. **This includes functions imported** by those
modules, **as well as any helper functions** defined within those modules.  To
prevent inadvertent exposure of non-action functions through the action api,
care should be taken to:

1. Import modules correctly (see :ref:`imports`).  For example::

     import ckan.lib.search as search

     search.query_for(...)

2. Hide any locally defined helper functions: ::

     def _a_useful_helper_function(x, y, z):
        '''This function is not exposed because it is marked as private```
        return x+y+z

3. Bring imported convenience functions into the module namespace as private
   members: ::

     _get_or_bust = logic.get_or_bust


Use ``get_action()``
````````````````````

Don't call ``logic.action`` functions directly, instead use ``get_action()``.
This allows plugins to override action functions using the ``IActions`` plugin
interface. For example::

    ckan.logic.get_action('group_activity_list_html')(...)

Instead of ::

    ckan.logic.action.get.group_activity_list_html(...)


Auth Functions and ``check_access()``
`````````````````````````````````````

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
```````````````````````

The ``data_dict`` parameter of logic action functions may be user provided, so
required files may be invalid or absent. Naive Code like::

  id = data_dict['id']

may raise a ``KeyError`` and cause CKAN to crash with a 500 Server Error
and no message to explain what went wrong. Instead do::

  id = _get_or_bust(data_dict, "id")

which will raise ``ValidationError`` if ``"id"`` is not in ``data_dict``. The
``ValidationError`` will be caught and the user will get a 400 Bad Request
response and an error message explaining the problem.


Validation and ``ckan.logic.schema``
````````````````````````````````````

Logic action functions can use schema defined in ``ckan.logic.schema`` to
validate the contents of the ``data_dict`` parameters that users pass to them.

An action function should first check for a custom schema provided in the
context, and failing that should retrieve its default schema directly, and
then call ``_validate()`` to validate and convert the data. For example, here
is the validation code from the ``user_create()`` action function::

 schema = context.get('schema') or ckan.logic.schema.default_user_schema()
 session = context['session']
 validated_data_dict, errors = _validate(data_dict, schema, context)
 if errors:
     session.rollback()
     raise ValidationError(errors)


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

Please see :doc:`extensions/index` for information about writing ckan
extensions, including details on the API available to extensions.

Deprecation
-----------

- Anything that may be used by extensions (see :doc:`extensions/index`) needs
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

