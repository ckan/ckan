=============================================
Internationalizating of strings in extensions
=============================================

.. seealso::

   In order to internationalize you extension you must mark the strings for
   internationalization. You can find out how to do this by reading
   :doc: `/contributing/frontend/string-i18n.rst`
   
.. seealso::

   In this tutorial we are assuming that you have read the
   :doc: `/extensions/tutorial`

We will create a simple extension that demonstrates the translation of strings
inside extensions. After running 

    paster --plugin=ckan create -t ckanext ckanext-itranslation

Change and simply the ``plugin.py`` file to be 

.. literalinclude:: ../../ckanext/example_itranslation/plugin_v1.py

Add a template file ``ckanext-itranslation/templates/home/index.html``
containing

.. literalinclude:: ../../ckanext/example_itranslation/templates/home/index.html

This template just provides a sample string that we will be internationalizing
in this tutorial.

------------------
Extracting strings
------------------

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
internationalization to an older extension, you may need to add these them.
If you have your templates in a directory differing from the default location,
you may need to change the ``message_extractors`` stanza, you can read more
about message extractors at the `babel documentation <http://babel.pocoo.org/docs/messages/#extraction-method-mapping-and-configuration>`_


Add an directory to store your translations

    mkdir ckanext-itranslations/i18n

Next you will need a babel config file. Add ``setup.cfg`` file containing

.. literalinclude:: ../../ckanext/example_itranslation/setup.cfg

This file tells babel where the translation files are stored.
You can then run the ``extract_messages`` command to extract the strings from
your extension

    python setup.py extract_messages

This will create a template PO file named 
``ckanext/itranslations/i18n/ckanext-itranslation.pot``
At this point, you can either upload an manage your translations using
transifex or manually create your translations.

------------------------------
Creating translations manually
------------------------------

We will be creating translation files for the ``fr`` locale.
Create the translation PO files for the locale that you are translating for
by running `init_catalog <http://babel.pocoo.org/docs/setup/#init-catalog>`_

    python setup.py init_catalog -l fr

This will generate a file called ``i18n/fr/LC_MESSAGES/ckanext-itranslation.po``.
Edit this file to contain the following.

.. literalinclude:: ../../ckanext/example_itranslation/i18n/fr/LC_MESSAGES/ckanext-example_itranslation.po
    :lines: 17-19


---------------------------
Translations with Transifex
---------------------------

Once you have created your translations, you can manage them using Transifex,
this is out side of the scope of this tutorial, but the Transifex documentation
provides tutorials on how to 
`upload translations <http://docs.transifex.com/tutorials/content/#upload-files-and-download-the-translations>`_
and how to manage them using them 
`command line client <http://docs.transifex.com/tutorials/client/>`_


---------------------
Compiling the catalog
---------------------

Now compile the PO files by running

    python setup.py compile_catalog -l fr

This will generate an mo file containing your translations.

--------------------------
The ITranslation interface
--------------------------

Once you have created the translated strings, you will need to inform CKAN that
your extension is translated by implementing the ``ITranslation`` interface in
your extension. Edit your ``plugin.py`` to contain the following.

.. literalinclude:: ../../ckanext/example_itranslation/plugin.py
    :emphasize-lines: 3, 6-7

Your done! To test your translated extension, make sure you add the extension to
your |development.ini| and run a ``paster serve`` and browse to
http://localhost:5000. You should find that switching to the ``fr`` locale in
the web interface should change the home page string to ``this is an itranslated
string``


Advanced ITranslation usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are translating a CKAN extension that already exists, or you have
structured your extension differently from the default layout. You may
have to tell CKAN where to locate your translated files, you can do this by
having your plugin not inherit from the ``DefaultTranslation`` class and
implement the ``ITranslation`` interface yourself.

.. autosummary::

   ~ckan.plugins.interfaces.ITranslation.i18n_directory
   ~ckan.plugins.interfaces.ITranslation.i18n_locales
   ~ckan.plugins.interfaces.ITranslation.i18n_domain
