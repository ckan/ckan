=====================================
Best practices for writing extensions
=====================================


------------------------------
Follow CKAN's coding standards
------------------------------

See :doc:`/contributing/index`.


-------------------------------------------------
Use the plugins toolkit instead of importing CKAN
-------------------------------------------------

Try to limit your extension to interacting with CKAN only through CKAN's
:doc:`plugin interfaces <plugin-interfaces>` and
:doc:`plugins toolkit <plugins-toolkit>`. It's a good idea to keep your
extension code separate from CKAN as much as possible, so that internal changes
in CKAN from one release to the next don't break your extension.


---------------------------------
Don't edit CKAN's database tables
---------------------------------

An extension can create its own tables in the CKAN database, but it should *not*
write to core CKAN tables directly, add columns to core tables, or use foreign
keys against core tables.


-------------------------------------------------------
Implement each plugin class in a separate Python module
-------------------------------------------------------

This keeps CKAN's plugin loading order simple, see :ref:`ckan.plugins`.


.. _extension config setting names best practice:

-----------------------------------------------------------------
Names of config settings should include the name of the extension
-----------------------------------------------------------------

Names of config settings provided by extensions should include the name
of the extension, to avoid conflicting with core config settings or with
config settings from other extensions. For example::

  ckan.my_extension.show_most_popular_groups = True


-------------------------------------
Internationalize user-visible strings
-------------------------------------

All user-visible strings should be internationalized, see
:doc:`/contributing/string-i18n`.
