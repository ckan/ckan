======================================
Best practices for writing CKAN themes
======================================

.. _don't use c:

---------------
Don't use ``c``
---------------

As much as possible, avoid accessing the Pylons template context :py:data:`c`
(or :py:data:`tmpl_context`). :py:data:`c` is a thread-global variable, which
encourages spaghetti code that's difficult to understand and to debug.

Instead, have controller methods add variables to the :py:data:`extra_vars`
parameter of :py:func:`~ckan.lib.base.render`, or have the templates
call
:doc:`template helper functions <template-helper-functions>` instead.

:py:data:`extra_vars` has the advantage that it allows templates, which are
difficult to debug, to be simpler and shifts logic into the easier-to-test and
easier-to-debug Python code. On the other hand, template helper functions are
easier to reuse as they're available to all templates and they avoid
inconsistencies between the namespaces of templates that are rendered by
different controllers (e.g. one controller method passes the package dict as an
extra var named ``package``, another controller method passes the same thing
but calls it ``pkg``, a third calls it ``pkg_dict``).

You can use the :py:class:`~ckan.plugins.interfaces.ITemplateHelpers` plugin
interface to add custom helper functions, see
:ref:`custom template helper functions`.


-----------------
Use ``url_for()``
-----------------

Always use :py:func:`~ckan.lib.helpers.url_for` (available to templates as
``h.url_for()``) when linking to other CKAN pages, instead of hardcoding URLs
like ``<a href="/dataset">``. Links created with
:py:func:`~ckan.lib.helpers.url_for` will update themselves if the URL routing
changes in a new version of CKAN, or if a plugin changes the URL routing.


---------------------------------------------------------------------
Use ``{% trans %}``, ``{% pluralize %}``, ``_()`` and ``ungettext()``
---------------------------------------------------------------------

All user-visible strings should be internationalized, see
:doc:`/contributing/string-i18n`.


------------------
Avoid name clashes
------------------

See :ref:`avoid name clashes`.


.. _javascript module docstrings best practice:

-------------------------------------------
|javascript| modules should have docstrings
-------------------------------------------

A |javascript| module should have a docstring at the top of the file, briefly
documentating what the module does and what options it takes. For example:

.. literalinclude:: /../ckanext/example_theme_docs/v17_popover/assets/example_theme_popover.js
   :language: javascript


.. _pubsub unsubscribe best practice:

-------------------------------------------------------------------
JavaScript modules should unsubscribe from events in ``teardown()``
-------------------------------------------------------------------

Any JavaScript module that calls :js:func:`this.sandbox.client.subscribe`
should have a ``teardown()`` function that calls
:js:func:`~this.sandbox.client.unsubscribe`, to prevent memory leaks.
CKAN calls the ``teardown()`` functions of modules when those modules are
removed from the page.

.. _pubsub overuse best practice:

--------------------
Don't overuse pubsub
--------------------

There shouldn't be very many cases where a JavaScript module really needs to
use :ref:`Pubsub <pubsub>`, try to only use it when you really need to.

JavaScript modules in CKAN are designed to be small and loosely-coupled,
for example modules don't share any global variables and don't call
each other's functions. But pubsub offers a way to tightly couple JavaScript
modules together, by making modules depend on multiple events published by
other modules. This can make the code buggy and difficult to understand.


--------------------------------------------
Use ``{% snippet %}``, not ``{% include %}``
--------------------------------------------

Always use CKAN's custom ``{% snippet %}`` tag instead of Jinja's default
``{% include %}`` tag. Snippets can only access certain global variables, and
any variables explicitly passed to them by the calling template. They don't
have access to the full context of the calling template, as included files do.
This makes snippets more reusable, and much easier to debug.


.. _snippet docstrings best practice:

-------------------------------
Snippets should have docstrings
-------------------------------

A snippet should have a docstring comment at the top of the file that briefly
documents what the snippet does and what parameters it requires. For example:

.. literalinclude:: /../ckanext/example_theme_docs/v10_custom_snippet/templates/snippets/example_theme_most_popular_groups.html
   :language: django
