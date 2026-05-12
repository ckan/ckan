========================================
Internationalizing strings in extensions
========================================

.. seealso::

   In order to internationalize your extension you must :doc:`mark its strings
   for internationalization </contributing/string-i18n>`. See also
   :doc:`/contributing/i18n`.

   This tutorial assumes that you have read the :doc:`/extensions/tutorial`.

We will create a simple extension to demonstrate the translation of strings
inside extensions. After running::

    ckan -c |ckan.ini| create -t ckanext ckanext-itranslation

Change the ``plugin.py`` file to:

.. literalinclude:: ../../ckanext/example_itranslation/plugin_v1.py

Add a template file ``ckanext-itranslation/templates/home/index.html``
containing:

.. literalinclude:: ../../ckanext/example_itranslation/templates/home/index.html

This template provides a sample string that we will internationalize in this
tutorial.

.. note::

    While this tutorial only covers Python/Jinja templates it is also possible
    (since CKAN 2.7) to :ref:`translate strings in an extension's JavaScript
    modules <javascript_i18n>`.

---------------
Extract strings
---------------

.. tip::

   If you have generated a new extension whilst following this tutorial the
   default template will have generated these files for you and you can simply
   run the ``extract_messages`` command immediately.

Check your ``setup.py`` file in your extension for the following lines

.. code-block:: python
    :emphasize-lines: 5-6, 12-15

    setup(
        entry_points='''
            [ckan.plugins]
            itranslation=ckanext.itranslation.plugin:ExampleITranslationPlugin
            [babel.extractors]
            ckan = ckan.lib.extract:extract_ckan
        '''

        message_extractors={
            'ckanext': [
                ('**.py', 'python', None),
                ('**.js', 'javascript', None),
                ('**/templates/**.html', 'ckan', None),
            ],
        }

These lines will already be present in our example, but if you are adding
internationalization to an older extension, you may need to add them.
If you have your templates in a directory differing from the default location
(``ckanext/yourplugin/i18n``),
you may need to change the ``message_extractors`` stanza. You can read more
about message extractors in the `babel documentation <http://babel.pocoo.org/docs/messages/#extraction-method-mapping-and-configuration>`_.


Add a directory to store your translations::

    mkdir ckanext-itranslations/ckanext/itranslations/i18n

Next you will need a babel config file. Add a ``setup.cfg`` file containing the
following (make sure you replace ``itranslations`` with the name of your extension):

.. literalinclude:: ../../ckanext/example_itranslation/setup.cfg

This file tells babel where the translation files are stored.
You can then run the ``extract_messages`` command to extract the strings from
your extension::

    python setup.py extract_messages

This will create a template PO file named
``ckanext/itranslations/i18n/ckanext-itranslation.pot``.

At this point, you can either upload and manage your translations using
Transifex or manually edit your translations.

----------------------------
Manually create translations
----------------------------

We will create translation files for the ``fr`` locale. Create the translation
PO files for the locale that you are translating for by running `init_catalog
<http://babel.pocoo.org/en/latest/setup.html#init-catalog>`_::

    python setup.py init_catalog -l fr

This will generate a file called ``i18n/fr/LC_MESSAGES/ckanext-itranslation.po``.
This file should contain the untranslated string on our template. You can manually add
a translation for it by editing the ``msgstr`` section:

.. literalinclude:: ../../ckanext/example_itranslation/i18n/fr/LC_MESSAGES/ckanext-example_itranslation.po
    :lines: 17-19


---------------------------
Translations with Transifex
---------------------------

Once you have created your translations, you can manage them using Transifex.
This is out side of the scope of this tutorial, but the Transifex documentation
provides tutorials on how to
`upload translations <https://help.transifex.com/en/articles/6318456-uploading-translations>`_
and how to manage them using the
`command line client <https://developers.transifex.com/docs/using-the-client>`_.


---------------------
Compiling the catalog
---------------------

Once the translation files (``po``) have been updated, either manually or via Transifex, compile them
by running::

    python setup.py compile_catalog

This will generate a ``mo`` file containing your translations that can be used by CKAN.

--------------------------
The ITranslation interface
--------------------------

Once you have created the translated strings, you will need to inform CKAN that
your extension is translated by implementing the ``ITranslation`` interface in
your extension. Edit your ``plugin.py`` to contain the following.

.. literalinclude:: ../../ckanext/example_itranslation/plugin.py
    :emphasize-lines: 3, 6-7

You're done! To test your translated extension, make sure you add the extension to
your |ckan.ini|, run a ``ckan run`` command and browse to
http://localhost:5000. You should find that switching to the ``fr`` locale in
the web interface will change the home page string to ``this is an itranslated
string``.


Advanced ITranslation usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are translating a CKAN extension that already exists, or you have
structured your extension differently from the default layout. You may have to
tell CKAN where to locate your translated files, you can do this by not having
your plugin inherit from the ``DefaultTranslation`` class and instead
implement the ``ITranslation`` interface yourself.

.. autosummary::

   ~ckan.plugins.interfaces.ITranslation.i18n_directory
   ~ckan.plugins.interfaces.ITranslation.i18n_locales
   ~ckan.plugins.interfaces.ITranslation.i18n_domain
