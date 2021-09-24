.. include:: ./substitutions.rst

==============================================
Variables and functions available to templates
==============================================

The following global variables and functions are available to all CKAN
templates in their top-level namespace:

.. note::

   In addition to the global variables listed below, each template also has
   access to variables from a few other sources:

   * Any extra variables explicitly passed into a template by the controller
     that rendered the template will also be available to that template, in its
     top-level namespace. Any variables explicitly added to the template
     context variable :py:data:`c` will also be available to the template as
     attributes of :py:data:`c`.

     To see which additional global variables and context attributes are
     available to a given template, use CKAN's
     :ref:`debug footer <debug footer>`.

   * Any variables explicitly passed into a template snippet in the calling
     ``{% snippet %}`` tag will be available to the snippet in its top-level
     namespace. To see these variables, use the
     :ref:`debug footer <debug footer>`.

   * Jinja2 also makes a number of filters, tests and functions available in
     each template's global namespace. For a list of these, see the
     `Jinja2 docs`_.

.. py:data:: tmpl_context

   The `Pylons template context object <https://thejimmyg.github.io/pylonsbook/en/1.0/exploring-pylons.html?highlight=template%20context#context-object>`_,
   a thread-safe object that the application can store request-specific
   variables against without the variables associated with one HTTP request
   getting confused with variables from another request.

   ``tmpl_context`` is usually abbreviated to ``c`` (an alias).

   Using ``c`` in CKAN is discouraged, use template helper functions instead.
   See :ref:`don't use c`.

   ``c`` is not available to snippets.

.. py:data:: c

   An alias for :py:data:`tmpl_context`.

.. py:data:: app_globals

   The `Pylons App Globals object <https://thejimmyg.github.io/pylonsbook/en/1.0/exploring-pylons.html?highlight=template%20context#app-globals-object>`_,
   an instance of the :py:class:`ckan.lib.app_globals.Globals` class.
   The application can store request-independent variables
   against the ``app_globals`` object. Variables stored against
   ``app_globals`` are shared between all HTTP requests.

.. py:data:: g

   An alias for :py:data:`app_globals`.

.. py:data:: h

   CKAN's :ref:`template helper functions <template helper functions>`, plus
   any
   :ref:`custom template helper functions <custom template helper functions>`
   provided by any extensions.

.. py:data:: request

   The `Pylons Request object <https://thejimmyg.github.io/pylonsbook/en/1.0/exploring-pylons.html?highlight=request#request>`_,
   contains information about the HTTP request that is currently being
   responded to, including the request headers and body, URL parameters, the
   requested URL, etc.

.. py:data:: response

   The `Pylons Response object <https://thejimmyg.github.io/pylonsbook/en/1.0/exploring-pylons.html?highlight=request#response>`_,
   contains information about the HTTP response that is currently being
   prepared to be sent back to the user, including the HTTP status code,
   headers, cookies, etc.

.. py:data:: session

   The `Beaker session object <http://beaker.readthedocs.org/en/latest/>`_,
   which contains information stored in the user's currently active session
   cookie.

.. py:function:: _()

   The `pylons.i18n.translation.ugettext(value) <http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/modules/i18n_translation.html?highlight=ugettext#pylons.i18n.translation.ugettext>`_ function:

    Mark a string for translation. Returns the localized unicode string of
    value.

    Mark a string to be localized as follows::

     _('This should be in lots of languages')

.. py:function:: N_()

   The `pylons.i18n.translation.gettext_noop(value) <http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/modules/i18n_translation.html?highlight=gettext_noop#pylons.i18n.translation.gettext_noop>`_ function:

    Mark a string for translation without translating it. Returns value.

    Used for global strings, e.g.::

        foo = N_('Hello')

        class Bar:
            def __init__(self):
                self.local_foo = _(foo)

        h.set_lang('fr')
        assert Bar().local_foo == 'Bonjour'
        h.set_lang('es')
        assert Bar().local_foo == 'Hola'
        assert foo == 'Hello'


.. py:function:: ungettext

   The `pylons.i18n.translation.ungettext(singular, plural, n) <http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/modules/i18n_translation.html?highlight=ungettext#pylons.i18n.translation.ungettext>`_
   function:

    Mark a string for translation. Returns the localized unicode string of the
    pluralized value.

    This does a plural-forms lookup of a message id. singular is used as the
    message id for purposes of lookup in the catalog, while n is used to
    determine which plural form to use. The returned message is a Unicode
    string.

    Mark a string to be localized as follows::

      ungettext('There is %(num)d file here', 'There are %(num)d files here',
                n) % {'num': n}

.. py:data:: translator

   An instance of the `gettext.NullTranslations <http://docs.python.org/2/library/gettext.html#the-nulltranslations-class>`_
   class. This is for internal use only, templates shouldn't need to use this.


.. py:class:: actions

   The :py:class:`ckan.model.authz.Action` class.

   .. todo:: Remove this? Doesn't appear to be used and doesn't look like
             something we want.
