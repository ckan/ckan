===========================
String internationalization
===========================


All user-facing Strings in CKAN Python, JavaScript and Jinja2 code should be
internationalized, so that our translators can then localize the
strings for each of the many languages that CKAN supports. This guide shows
CKAN developers how to internationalize strings, and what to look for regarding
string internationalization when reviewing a pull request.

.. note::

   *Internationalization* (or i18n) is the process of marking strings for
   translation, so that the strings can be extracted from the source code and
   given to translators.
   *Localization* (l10n) is the process of translating the marked strings into
   different languages.

.. seealso::

  :doc:`i18n`
    If you want to translate CKAN, this page documents
    the process that translators follow to localize CKAN into different
    languages.

  :doc:`release-process`
    The processes for extracting internationalized strings from CKAN and
    uploading them to Transifex to be translated, and for downloading the
    translations from Transifex and loading them into CKAN to be displayed
    are documented on this page.

.. note::

   Much of the existing code in CKAN was written before we had these
   guidelines, so it doesn't always do things as described on this page.
   When writing new code you should follow the guidelines on this page, not the
   existing code.


.. _jinja_i18n:

------------------------------------------------
Internationalizating strings in Jinja2 templates
------------------------------------------------

Most user-visible strings should be in the Jinja2 templates, rather than in
Python or JavaScript code. This doesn't really matter to translators, but it's
good for the code to separate logic and content.  Of course this isn't always
possible. For example when error messages are delivered through the API,
there's no Jinja2 template involved.

The preferred way to internationalize strings in Jinja2 templates is by using
`the trans tag from Jinja2's i18n extension <http://jinja.pocoo.org/docs/templates/#i18n>`_,
which is available to all CKAN core and extension templates and snippets.

Most of the following examples are taken from the Jinja2 docs.

To internationalize a string put it inside a ``{% trans %}`` tag:

.. code-block:: jinja

   <p>{% trans %}This paragraph is translatable.{% endtrans %}</p>

You can also use variables from the template's namespace inside a
``{% trans %}``:

.. code-block:: jinja

   <p>{% trans %}Hello {{ user }}!{% endtrans %}</p>

(Only variable tags are allowed inside trans tags, not statements.)

You can pass one or more arguments to the ``{% trans %}`` tag to bind variable
names for use within the tag:

.. code-block:: jinja

   <p>{% trans user=user.username %}Hello {{ user }}!{% endtrans %}</p>

  {% trans book_title=book.title, author=author.name %}
  This is {{ book_title }} by {{ author }}
  {% endtrans %}

To handle different singular and plural forms of a string, use a ``{% pluralize
%}`` tag:

.. code-block:: jinja

   {% trans count=list|length %}
   There is {{ count }} {{ name }} object.
   {% pluralize %}
   There are {{ count }} {{ name }} objects.
   {% endtrans %}

(In English the first string will be rendered if ``count`` is 1, the second
otherwise.  For other languages translators will be able to provide their own
strings for different values of ``count``.)

The first variable in the block (``count`` in the example above) is used to
determine which of the singular or plural forms to use. Alternatively you can
explicitly specify which variable to use:

.. code-block:: jinja

   {% trans ..., user_count=users|length %}
      ...
   {% pluralize user_count %}
      ...
   {% endtrans %}

The ``{% trans %}`` tag is preferable, but if you need to pluralize a string
within a Jinja2 expression you can use the ``_()`` and ``ungettext()``
functions:

.. code-block:: jinja

   {% set hello = _('Hello World!') %}

To use variables in strings, use Python `format string syntax`_
and then call the ``.format()`` method on the string that ``_()`` returns:

.. _format string syntax: https://docs.python.org/2/library/string.html#formatstrings

.. code-block:: jinja

   {% set hello = _('Hello {name}!').format(name=user.name) %}

Singular and plural forms are handled by ``ungettext()``:

.. code-block:: jinja

   {% set text = ungettext(
          '{num} apple', '{num} apples', num_apples).format(num=num_apples) %}

.. note::

   There are also ``gettext()`` and ``ngettext()`` functions available to
   templates, but we recommend using ``_()`` and ``ungettext()`` for
   consistency with CKAN's Python code.
   This deviates from the Jinja2 docs, which do use ``gettext()`` and
   ``ngettext()``.

   ``_()`` is not an alias for ``gettext()`` in CKAN's Jinja2 templates,
   ``_()`` is the function provided by Pylons, whereas ``gettext()`` is the
   version provided by Jinja2, their behaviors are not exactly the same.


-----------------------------------------
Internationalizing strings in Python code
-----------------------------------------

CKAN uses the :py:func:`~flask_babel._` and :py:func:`~flask_babel.ngettext`
functions from the `Flask-Babel`_ library to internationalize
strings in Python code.

.. _Flask-Babel: https://pythonhosted.org/Flask-Babel/

.. note::
    Code running on Pylons will use the functions provided by
    the `pylons.i18n.translation`_ module, but their behaviour is the same.

.. _pylons.i18n.translation: http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/modules/i18n_translation.html#module-pylons.i18n.translation

Core CKAN modules should import :py:func:`~ckan.common._` and
:py:func:`~ckan.common.ungettext` from :py:mod:`ckan.common`,
i.e. ``from ckan.common import _, ungettext``
(don't import :py:func:`flask_babel._` or :py:func:`pylons.i18n.translation._` directly, for example).

CKAN plugins should import :py:mod:`ckan.plugins.toolkit` and use
:py:func:`ckan.plugins.toolkit._` and
:py:func:`ckan.plugins.toolkit.ungettext`, i.e. do
``import ckan.plugins.toolkit as toolkit`` and then use ``toolkit._()`` and
``toolkit.ungettext()`` (see :doc:`/extensions/plugins-toolkit`).

To internationalize a string pass it to the ``_()`` function:

.. code-block:: python

   my_string = _("This paragraph is translatable.")

To use variables in a string, call the ``.format()`` method on the translated
string that ``_()`` returns:

.. code-block:: python

   hello = _("Hello {user}!").format(user=user.name)

   book_description = _("This is { book_title } by { author }").format(
       book_title=book.title, author=author.name)

To handle different plural and singular forms of a string, use ``ungettext()``:

.. code-block:: python

   translated_string = ungettext(
       "There is {count} {name} object.",
       "There are {count} {name} objects.",
       num_objects).format(count=count, name=name)


.. _javascript_i18n:

---------------------------------------------
Internationalizing strings in JavaScript code
---------------------------------------------

Each :ref:`CKAN JavaScript module <javascript_modules>` offers the methods
``_`` and ``ngettext``. The ``ngettext`` function is used to translate a single string which
has both a singular and a plural form, whereas ``_`` is used to translate a single string only:

.. code-block:: javascript

    this.ckan.module('i18n-demo', function($) {
        return {
            initialize: function () {
                console.log(this._('Translate me!'));
                console.log(this.ngettext('%(num)d item', '%(num)d items', 3));
            }
        };
    };

To translate a fixed singular string, use ``_``. It returns the translation of
the string for the currently selected locale. If the current locale doesn't
provide a translation for the string then it is returned unchanged.

.. code-block:: javascript

    this._('Something that should be translated')

Placeholders are supported via `sprintf-syntax`_, the corresponding values are
passed via another parameter:

.. _sprintf-syntax: http://www.diveintojavascript.com/projects/javascript-sprintf

.. code-block:: javascript

    this._("My name is %(name)s and I'm from %(hometown)s.",
           {name: 'Sarah', hometown: 'Cape Town'})

``ngettext`` allows you to translate a string that may be either singular or
plural, depending on some variable:

.. code-block:: javascript

    this.ngettext('Deleted %(num)d item',
                  'Deleted %(num)d items',
                  items.length)

If ``items.length`` is 1 then the translation for the first argument will be
returned, otherwise that of the second argument. ``num`` is a magical
placeholder that is automatically provided by ``ngettext`` and contains the
value of the third parameter.

Like ``_``, ``ngettext`` can take additional placeholders:

.. code-block:: javascript

    this.ngettext("I'm %(name)s and I'm %(num)d year old",
                  "I'm %(name)s and I'm %(num)d years old",
                  age,
                  {name: 'John'})


.. note::

    CKAN's JavaScript code automatically downloads the appropriate translations
    at request time from the CKAN server. Since CKAN 2.7 the corresponding
    translation files are regenerated automatically if necessary when CKAN
    starts.

    You can also regenerate the translation files manually using
    ``ckan translation js``:

    .. parsed-literal::

        python setup.py extract_messages  # Extract translatable strings
        # Update .po files as desired
        python setup.py compile_catalog   # Compile .mo files for Python/Jinja
        ckan -c |ckan.ini| translation js         # Compile JavaScript catalogs


.. note::

    Prior to CKAN 2.7, JavaScript modules received a similar but different
    ``_`` function for string translation as a parameter. This is still
    supported but deprecated and will be removed in a future release.

-------------------------------------------------
General guidelines for internationalizing strings
-------------------------------------------------

Below are some guidelines to follow when marking your strings for translation.
These apply to strings in Jinja2 templates or in Python or JavaScript code.
These are mostly meant to make life easier for translators, and help to improve
the quality of CKAN's translations:

* Leave as much HTML and other code out of the translation string as possible.

  For example, don't include surrounding ``<p>...</p>`` tags in the marked
  string. These aren't necessary for the translator to do the translation,
  and if the translator accidentally changes them in the translation string
  the HTML will be broken.

  Good:

  .. code-block:: jinja

     <p>{% trans %}Don't put HTML tags inside translatable strings{% endtrans %}</p>

  Bad (``<p>`` tags don't need to be in the translation string):

  .. code-block:: python

     mystring = _("<p>Don't put HTML tags inside translatable strings</p>")

* But don't split a string into separate strings.

  Translators need as much context as possible to translate strings well, and
  if you split a string up into separate strings and mark each for translation
  separately, translators must translate each of these separate strings in
  isolation. Also, some languages may need to change the order of words in a
  sentence or even change the order of sentences in a paragraph, splitting
  into separate strings makes assumptions about word order.

  It's better to leave HTML tags or other code in strings than to split a
  string.  For example, it's often best to leave HTML ``<a>`` tags in rather
  than split a string.

  Good:

  .. code-block:: python

     _("Don't split a string containing some <b>markup</b> into separate strings.")

  Bad (text will be difficult to translate or untranslatable):

  .. code-block:: python

     _("Don't split a string containing some ") + "<b>" + _("markup") + </b> + _("into separate strings.")

* You can split long strings over multiple lines using parentheses to avoid
  long lines, Python will concatenate them into a single string:

  Good:

  .. code-block:: python

     _("This is a really long string that would just make this line far too "
       "long to fit in the window")

* Leave unnecessary whitespace out of translatable strings, but do put
  punctuation into translatable strings.

* Try not to make translators translate strings that don't need to be
  translated.

  For example, ``'templates'`` is the name of a directory, it doesn't
  need to be marked for translation.

* Mark singular and plural forms of strings correctly.

  In Jinja2 templates this means using ``{% trans %}`` and ``{% pluralize %}``
  or ``ungettext()``. In Python it means using ``ungettext()``. See above
  for examples.

  Singular and plural forms work differently in different languages.
  For example English has singular and plural nouns, but Slovenian has
  singular, dual and plural.

  Good:

  .. code-block:: python

     num_people = 4
     translated_string = ungettext(
         'There is one person here',
         'There are {num_people} people here',
         num_people).format(num_people=num_people)

  Bad (this assumes that all languages have the same plural forms as English):

  .. code-block:: python

     if num_people == 1:
         translated_string = _('There is one person here')
     else:
         translated_string = _(
             'There are {num_people} people here'.format(num_people=num_people))

* Don't use `old-style %s string formatting <https://docs.python.org/2/library/stdtypes.html#string-formatting>`_
  in Python, use the new `.format() method`_
  instead.

  Strings formatted with ``.format()`` give translators more context.
  The ``.format()`` method is also more expressive, and is the preferred way
  to format strings in Python 3.

  Good:

  .. code-block:: python

     "Welcome to {site_title}".format(site_title=site_title)

  Bad (not enough context for translators):

  .. code-block:: python

     "Welcome to %s" % site_title

* Use descriptive names for replacement fields in strings.

  This gives translators more context.

  Good:

  .. code-block:: python

     "Welcome to {site_title}".format(site_title=site_title)

  Bad (not enough context for translators):

  .. code-block:: python

     "Welcome to {0}".format(site_title)

  Worse (doesn't work in Python 2.6):

  .. code-block:: python

     "Welcome to {}".format(site_title)

* Use ``TRANSLATORS:`` comments to provide extra context for translators
  for difficult to find, very short, or obscure strings.

  For example, in Python:

  .. code-block:: python

     # TRANSLATORS: This is a helpful comment.
     _("This is an ambiguous string")

  In Jinja2:

  .. code-block:: jinja

     {# TRANSLATORS: This heading is displayed on the user's profile page. #}
     <h1>{% trans %}Heading{% endtrans %}</h1>

  In JavaScript:

  .. code-block:: javascript

      // TRANSLATORS: "Manual" refers to the user manual
      _("Manual")

  These comments end up in the ``ckan.pot`` file and translators will see them
  when they're translating the strings (Transifex shows them, for example).

  .. note::

     The comment must be on the line before the line with the ``_()``,
     ``ungettext()`` or ``{% trans %}``, and must start with the exact string
     ``TRANSLATORS:`` (in upper-case and with the colon). This string is
     configured in ``setup.cfg``.

.. todo::

   Explain how to use *message contexts*, where the same exact string may
   appear in two different places in the UI but have different meanings.

   For example "filter" can be a noun or a verb in English, and may need two
   different translations in another language. Currently if the string
   ``_("filter")`` appears in different places in CKAN this will only
   produce one string to be translated in the ``ckan.pot`` file.

   I think the right way to handle this with gettext is using ``msgctxt``,
   but it looks like babel doesn't support it yet.

.. todo::

   Explain how we internationalize dates, currencies and numbers
   (e.g. different positioning and separators used for decimal points in
   different languages).

.. _.format() method: https://docs.python.org/2/library/stdtypes.html#str.format
