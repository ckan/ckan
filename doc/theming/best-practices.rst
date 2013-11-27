======================================
Best practices for writing CKAN themes
======================================

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
extension. For example::

 example_theme_most_popular_groups


-------------------------------------------------------------
Snippet filenames should begin with the name of the extension
-------------------------------------------------------------

Namespacing snippets in this way avoids accidentally overriding, or being
overridden by, a core snippet, or a snippet from another extension.
For example::

 ckanext-example_theme/ckanext/example_theme/templates/snippets/example_theme_most_popular_groups.html


--------------------------------------------
Use ``{% snippet %}``, not ``{% include %}``
--------------------------------------------

Always use CKAN's custom ``{% snippet %}`` instead of Jinja's default
``{% include %}`` tag. Snippets can only access certain global variables, and
any variables explicitly passed to them by the calling template. They don't
have access to the full context of the calling template, as included files do.
This makes snippets much easier to debug.
