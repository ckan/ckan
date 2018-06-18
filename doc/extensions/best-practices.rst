=====================================
Best practices for writing extensions
=====================================


------------------------------
Follow CKAN's coding standards
------------------------------

See :doc:`/contributing/index`.


.. _use the plugins toolkit:

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


.. _avoid name clashes:

------------------
Avoid name clashes
------------------
Many of the names you pick for your identifiers and files must be unique in
relation to the names used by core CKAN and other extensions. To avoid
conflicts you should prefix any public name that your extension introduces with
the name of your extension. For example:

* The names of *configuration settings* introduced by your extension should
  have the form ``my_extension.my_config_setting``.

* The names of *templates and template snippets* introduced by your extension
  should begin with the name of your extension::

      snippets/my_extension_useful_snippet.html

  If you have add a lot of templates you can also put them into a separate
  folder named after your extension instead.

* The names of *template helper functions* introduced by your extension should
  begin with the name of your extension. For example:

  .. literalinclude:: /../ckanext/example_theme_docs/v08_custom_helper_function/plugin.py
     :pyobject: ExampleThemePlugin.get_helpers

* The names of *JavaScript modules* introduced by your extension should begin
  with the name of your extension. For example
  ``fanstatic/example_theme_popover.js``:

  .. literalinclude:: /../ckanext/example_theme_docs/v16_initialize_a_javascript_module/fanstatic/example_theme_popover.js

* The names of *API action functions* introduced by your extension should begin
  with the name of your extension. For example
  ``my_extension_foobarize_everything``.

* The names of *background job queues* introduced by your extension should
  begin with the name of your extension. For example
  ``my_extension:super-special-job-queue``.

In some situations, a resource may even be shared between multiple CKAN
*instances*, which requires an even higher degree of uniqueness for the
corresponding names. In that case, you should also prefix your identifiers with
the CKAN site ID, which is available via

::

    try:
        # CKAN 2.7 and later
        from ckan.common import config
    except ImportError:
        # CKAN 2.6 and earlier
        from pylons import config

    site_id = config[u'ckan.site_id']

Currently this only affects the :ref:`Redis database <ckan_redis_url>`:

* All *keys in the Redis database* created by your extension should be prefixed
  with both the CKAN site ID and your extension's name.


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

