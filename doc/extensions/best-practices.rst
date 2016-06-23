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


---------------------------------------------
Add third party libraries to requirements.txt
---------------------------------------------

If your extension requires third party libraries, rather than 
adding them to ``setup.py``, they should be added
to ``requirements.txt``, which can be installed with::

  pip install -r requirements.txt

To prevent accidental breakage of your extension through backwards-incompatible 
behaviour of newer versions of your dependencies, their versions should be pinned, 
such as::

  requests==2.7.0

On the flip side, be mindful that this could also create version conflicts with
requirements of considerably newer or older extensions.


--------------------------------------------------
Do not automatically modify the database structure
--------------------------------------------------

If your extension uses custom database tables then it needs to modify the
database structure, for example to add the tables after its installation or to
migrate them after an update. These modifications should not be performed
automatically when the extension is loaded, since this can lead to `dead-locks
and other problems`_.

Instead, create a :doc:`paster command </maintaining/paster>` which can be run separately.

.. _dead-locks and other problems: https://github.com/ckan/ideas-and-roadmap/issues/164

