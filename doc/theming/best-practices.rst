======================================
Best practices for writing CKAN themes
======================================

.. _don't use c:

---------------
Don't use ``c``
---------------

As much as possible, avoid accessing the Pylons template context :py:data:`c`
(or :py:data:`tmpl_context`). Use
:doc:`template helper functions <template-helper-functions>` instead.
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


-------------------------------
Use ``_()`` and ``ungettext()``
-------------------------------

Always use :py:func:`_` (or, if pluralizaton is needed, :py:func:`ungettext`)
to mark user-visible strings for localization.


-----------------------------------------------------------------
Helper function names should begin with the name of the extension
-----------------------------------------------------------------

Namespacing helper functions in this way avoids accidentally overriding, or
being overriden by, a core helper function, or a helper function from another
extension. For example:

.. literalinclude:: /../ckanext/example_theme/v08_custom_helper_function/plugin.py
   :pyobject: ExampleThemePlugin.get_helpers


.. _snippet filenames best practice:

-------------------------------------------------------------
Snippet filenames should begin with the name of the extension
-------------------------------------------------------------

Namespacing snippets in this way avoids accidentally overriding, or being
overridden by, a core snippet, or a snippet from another extension.
For example::

 snippets/example_theme_most_popular_groups.html


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

.. literalinclude:: /../ckanext/example_theme/v10_custom_snippet/templates/snippets/example_theme_most_popular_groups.html
   :language: django
