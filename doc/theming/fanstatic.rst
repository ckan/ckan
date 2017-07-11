=================================================
Adding CSS and |javascript| files using Fanstatic
=================================================

If you're adding CSS files to your theme, you can add them
using `Fanstatic <http://www.fanstatic.org/>`_ rather than the simple
:ref:`extra_public_paths` method described in :doc:`static-files`.
If you're adding a |javascript| module, you *must* use Fanstatic.

Using Fanstatic to add |javascript| and CSS files takes advantage
of Fanstatic's features, such as automatically serving minified files in
production, caching and bundling files together to reduce page load times,
specifying dependencies between files so that the files a page needs (and only
the files it needs) are always loaded, and other tricks to optimize page load
times.

.. note::

   CKAN will only serve ``*.js`` and ``*.css`` files as Fanstatic resources,
   other types of static files (eg. image files, PDF files) must be added
   using the :ref:`extra_public_paths` method described in :doc:`static-files`.

Adding a custom |javascript| or CSS file to CKAN using Fanstatic is simple.
We'll demonstrate by changing our previous custom CSS example (see :doc:`css`)
to serve the CSS file with Fanstatic.

1. First, create a ``fanstatic`` directory in your extension and move the CSS
   file from ``public`` into ``fanstatic``::

    ckanext-example_theme/
      ckanext/
        example_theme/
          public/
            promoted-image.jpg
          fanstatic/
            example_theme.css

2. Use CKAN's :py:func:`~ckan.plugins.toolkit.add_resource()` function to
   register your fanstatic directory with CKAN. Edit the ``update_config()``
   method in your ``plugin.py`` file:

   .. literalinclude:: /../ckanext/example_theme_docs/v15_fanstatic/plugin.py
      :pyobject: ExampleThemePlugin.update_config

3. Finally, edit your extension's ``templates/base.html`` file and use CKAN's
   custom Jinja2 tag ``{% resource %}`` instead of the normal ``<link>`` tag to
   import the file:

   .. literalinclude:: /../ckanext/example_theme_docs/v15_fanstatic/templates/base.html
      :language: django

.. note::

  You can put ``{% resource %}`` tags anywhere in any template, and Fanstatic
  will insert the necessary ``<style>`` and ``<script>`` tags to include your
  CSS and |javascript| files and their dependencies in the right places in
  the HTML output (CSS files in the HTML ``<head>``, |javascript| files at
  the bottom of the page).

  Resources will *not* be included on the line where the ``{% resource %}``
  tag is.

.. note::

  A config file can be used to configure how Fanstatic should serve each resource
  file (whether or not to bundle files, what order to include files in, whether
  to include files at the top or bottom of the page, dependencies between files,
  etc.) See :doc:`/contributing/frontend/resources` for details.
