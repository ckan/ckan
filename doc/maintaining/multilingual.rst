======================
Multilingual Extension
======================

For translating CKAN's web interface see :doc:`/contributing/i18n`. In addition to user interface internationalization, a CKAN administrator can also enter translations into CKAN's database for terms that may appear in the contents of datasets, groups or tags created by users. When a user is viewing the CKAN site, if the translation terms database contains a translation in the user's language for the name or description of a dataset or resource, the name of a tag or group, etc. then the translated term will be shown to the user in place of the original.

Setup and Configuration
-----------------------

By default term translations are disabled. To enable them, you have to specify the multilingual plugins using the ``ckan.plugins`` setting in your CKAN configuration file, for example:

::

  # List the names of CKAN extensions to activate.
  ckan.plugins = multilingual_dataset multilingual_group multilingual_tag

Of course, you won't see any terms getting translated until you load some term translations into the database. You can do this using the ``term_translation_update`` and ``term_translation_update_many`` actions of the CKAN API, See :doc:`/api/index` for more details.

Loading Test Translations
-------------------------

If you want to quickly test the term translation feature without having to provide your own translations, you can load CKAN's test translations into the database by running this command from your shell:

::

  ckan -c |ckan.ini| create-test-data translations

See :doc:`/maintaining/cli` for more details.

Testing The Multilingual Extension
----------------------------------

If you have a source installation of CKAN you can test the multilingual extension by running the tests located in ``ckanext/multilingual/tests``. You must first install the packages needed for running CKAN tests into your virtual environment, and then run this command from your shell:

::

  pytest --ckan-ini=test-core.ini ckanext/multilingual/tests

See :doc:`/contributing/test` for more information.
