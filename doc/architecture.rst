======================
CKAN Code Architecture
======================

This section tries to give some guidelines for writing code that is consistent
with the intended, overall design and architecture of CKAN, going from the lowest
to the highest layers.


Database
========

CKAN uses `SQLAlchemy <http://www.sqlalchemy.org/>`_ to handle communication between
CKAN source code and the `PostgreSQL database <http://www.postgresql.org/>`_.


Migrations
----------

When changes are made to the model classes in ``ckan.model`` that alter CKAN's
database schema, a migration script has to be added to migrate old CKAN
databases to the new database schema when they upgrade their copies of CKAN.
See :doc:`migration`.


Model
=====

The ``ckan/model/`` package corresponds to the model in the `Model-View-Controller
concept
<http://www.codinghorror.com/blog/2008/05/understanding-model-view-controller.html>`_
and contains classes for each of the entities stored in CKAN's database, e.g.
``ckan/model/package.py`` contains a ``Package`` class that represents CKAN data
packages, and contains the SQLAlchemy code for mapping between Package objects
in the CKAN source code and their corresponding table in the database.

.. note::

    Packages are now called 'datasets' in the CKAN interface, but in the source
    code you'll still find many places where they're referred to as packages.
    They mean the same thing.


Dictization
-----------

``ckan/lib/dictization/`` contains functions that transform CKAN model objects
such as Packages, Resources, etc. into dictionaries and vice-versa. The
templates that render the CKAN web interface and the JSON format used by the
CKAN API both work with these dictionary representations.


Encapsulate SQLAlchemy in ``ckan.model``
----------------------------------------

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


Logic
=====

``ckan/logic/`` contains all the functions that the API_, WUI_ and CLI_ use for
accessing and manipulating the data stored in CKAN. Whenever you want to get,
create, update or delete some object from CKAN's model you use some function
from the ``ckan/logic/action/`` package, for example there are functions
``package_show()``, ``package_create()``, ``package_update()`` and
``package_delete()`` for working with packages.

All communication with the model should be done in the logic layer, and not in
higher-level layers such as the controllers, which should use the logic layer
instead of accessing the model themselves.


Validation
----------

The logic action functions use schema defined in ``ckan.logic.schema`` to
validate data in the ``data_dict`` that is posted to CKAN by users via the
API_, WUI_ or CLI_. The schema in turn draw on validation and conversion
functions defined in ``ckan.logic.validators`` and ``ckan.logic.converters``.

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


Auth Functions
--------------

Each action function defined in ``ckan.logic.action`` should use its own
corresponding auth function defined in ``ckan.logic.auth`` to check if the user
is authorized to call it. Instead of calling its auth function directly, an
action function should go through ``ckan.logic.check_access()`` (which is aliased
``_check_access`` in the action modules) because this allows plugins to override
auth functions using the ``IAuthFunctions`` plugin interface. For example::

    def package_show(context, data_dict):
        _check_access('package_show', context, data_dict)

``check_access`` will raise an exception if the user is not authorized, which
the action function should not catch. When this happens the user will be shown
an authorization error in their browser (or will receive one in their response
from the API_).


Always go through the Action Functions
--------------------------------------

Whenever some code, for example in ``ckan.lib`` or ``ckan.controllers``, wants
to get, create, update or delete an object from CKAN's model it should do so by
calling a function from the ``ckan.logic.action`` package, and *not* by
accessing ``ckan.model`` directly.


Never call ``logic.action`` methods directly
--------------------------------------------

Use ``get_action()`` instead. This allows plugins to override action functions
using the ``IActions`` plugin interface. For example::

    ckan.logic.get_action('group_activity_list_html')(...)

Instead of ::

    ckan.logic.action.get.group_activity_list_html(...)


Safely accessing data provided by the user
------------------------------------------

The ``data_dict`` parameter of logic action functions may be user provided, so
required keys may be invalid or absent. Naive Code like::

  id = data_dict['id']

may raise a ``KeyError`` and cause CKAN to crash with a 500 Server Error
and no message to explain what went wrong. Instead do::

  id = _get_or_bust(data_dict, "id")

which will raise ``ValidationError`` if ``"id"`` is not in ``data_dict``. The
``ValidationError`` will be caught and the user will get a 400 Bad Request
response and an error message explaining the problem.



Interfaces
==========

.. _API:

API
---

The :doc:`api` exposes the functions in ``ckan.logic.action`` to the world. The
API URL for an action function is automatically generated from the function
name, for example ``ckan.logic.action.create.package_create()`` is exposed at
``/api/action/package_create``. See `Steve Yegge's Google platforms rant
<https://plus.google.com/112678702228711889851/posts/eVeouesvaVX>`_ for some
interesting discussion about APIs.

**All** publicly visible functions in the
``ckan.logic.action.{create,delete,get,update}`` namespaces will be exposed
through the :doc:`api`. **This includes functions imported** by those modules,
**as well as any helper functions** defined within those modules.  To prevent
inadvertent exposure of non-action functions through the action api, care should
be taken to:

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


.. _WUI:

Web User Interface (WUI)
------------------------

CKAN's Web User Interface is implemented by the controller classes in
``ckan/controllers/``. These classes call functions from ``ckan/logic/action/`` to
manipulate data, and return rendered template files from ``ckan/templates/``.
``ckan/config/routing.py`` contains the routing definitions that control which
requests get sent to which controller classes according to which URL was
requested (it uses `http://routes.groovie.org`).

Currently CKAN templates use the `Genshi template engine <http://genshi.edgewall.org>`_
but the upcoming CKAN 2.0 release will move to the much nicer and friendlier
`Jinja2 <http://jinja.pocoo.org>`_ by default. Genshi will still be supported so
that existing CKAN themes don't break.


.. _CLI:

Command Line Interface (CLI)
----------------------------

CKAN has a Command Line Interface that you can use to do lots of actions such as
managing datasets and users, etc. (Do ``paster --plugin=ckan --help`` from
CKAN's dir to see what's available.) It's implemented using `Paste Script
<http://pythonpaste.org/script/developer.html>`_.


Extensions
==========


Extensions are a way for an external code to hook up into CKAN and add or alter
behavior. See :doc:`writing-extensions` for more information.


Controller & Template Helper Functions
======================================

``ckan.lib.helpers`` contains helper functions that can be used from
``ckan.controllers`` or from templates. When developing for CKAN core, only use
the helper functions found in ``ckan.lib.helpers.__allowed_functions__``.


.. _Testing:

Testing
=======

- Functional tests which test the behaviour of the web user interface, and the
  APIs should be placed within ``ckan/tests/functional``.  These tests can be a
  lot slower to run than unit tests which don't access the database or solr.  So
  try to bear that in mind, and attempt to cover just what is neccessary, leaving
  what can be tested via unit-testing in unit-tests.

- ``nose.tools.assert_in`` and ``nose.tools.assert_not_in`` are only available
  in Python>=2.7.  So import them from ``ckan.tests``, which will provide
  alternatives if they're not available.

- The `mock`_ library can be used to create and interrogate mock objects.

See :doc:`test` for further information on testing in CKAN.

.. _mock: http://pypi.python.org/pypi/mock


Code Deprecation
=================

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


Further Reading
===============

:doc:`python-coding-standards`

:doc:`javascript-coding-standards`

:doc:`html-coding-standards`

:doc:`css-coding-standards`

:doc:`release-cycle`

:doc:`i18n`
