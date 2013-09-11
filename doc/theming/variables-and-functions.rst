==============================================
Variables and functions available to templates
==============================================

The following global variables and functions are available to all CKAN
templates in their top-level namespace:

``c``
  The `Pylons template context object <http://pylonsbook.com/en/1.0/exploring-pylons.html?highlight=template%20context#context-object>`_,
  a thread-safe object that the application can store request-specific
  variables against without the variables associated with one HTTP request
  getting confused with variables from another request.

  Using ``c`` in CKAN is discouraged, use template helper functions instead.

  ``c`` is not available to snippets.

``app_globals``
  The `Pylons App Globals object <http://pylonsbook.com/en/1.0/exploring-pylons.html?highlight=template%20context#app-globals-object>`_,
  an object that the application can store request-independent variables
  against. Variables stored against ``app_globals`` are shared between all HTTP
  requests.

``h``
  CKAN's :ref:`template helper functions <template helper functions>`, plus any
  :ref:`custom template helper functions <custom template helper functions>`
  provided by any extensions.

``request``
  The `Pylons Request object <http://pylonsbook.com/en/1.0/exploring-pylons.html?highlight=request#request>`_,
  contains information about the HTTP request that is currently being responded
  to, including the request headers and body, URL parameters, the requested
  URL, etc.

``response``
 The `Pylons Response object <http://pylonsbook.com/en/1.0/exploring-pylons.html?highlight=request#response>`_,
 contains information about the HTTP response that is currently being prepared
 to be sent back to the user, including the HTTP status code, headers, cookies,
 etc.

``session``
  The `Beaker session object <http://beaker.readthedocs.org/en/latest/>`_,
  which contains information stored in the user's currently active session
  cookie.

``N_``
 The ``gettext_noop()`` function.

``_``
 The ``ugettext()`` function.

``translator``
 The ``gettext.NullTranslations`` object.

``ungettext``
 The ``ungettext()`` function.

``actions``
 The :py:class:`ckan.model.authz.Action`

 .. todo:: Remove this? Doesn't appear to be used and doesn't look like
           something we want.

In addition to the above, any variables explicitly passed into a template by a
controller action method when it calls ``render()`` will also be available to
that template, in its top-level namespace.

Any variables explicitly passed into a template snippet in the calling ``{%
snippet %}`` tag will be available to the snippet in its top-level namespace,

.. todo:: Add links to the default stuff that Jinja provides to all templates.
