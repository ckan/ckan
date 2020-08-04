=================================================
Adding CSS and |javascript| files using Webassets
=================================================

If you're adding CSS files to your theme, you can add them
using `Webassets <https://webassets.readthedocs.io/en/latest/>`_ rather than the simple
:ref:`extra_public_paths` method described in :doc:`static-files`.
If you're adding a |javascript| module, you *must* use Webassets.

Using Webassets to add |javascript| and CSS files takes advantage
of Webassets' features, such as automatically serving minified files in
production, caching and bundling files together to reduce page load times,
specifying dependencies between files so that the files a page needs (and only
the files it needs) are always loaded, and other tricks to optimize page load
times.

.. note::

   CKAN will only serve ``*.js`` and ``*.css`` files as Webassets resources,
   other types of static files (eg. image files, PDF files) must be added
   using the :ref:`extra_public_paths` method described in :doc:`static-files`.

Adding a custom |javascript| or CSS file to CKAN using Webassets is simple.
We'll demonstrate by changing our previous custom CSS example (see :doc:`css`)
to serve the CSS file with Webassets.

1. First, create an ``assets`` directory in your extension and move the CSS
   file from ``public`` into ``assets``::

    ckanext-example_theme/
      ckanext/
        example_theme/
          public/
            promoted-image.jpg
          assets/
            example_theme.css

2. Use CKAN's :py:func:`~ckan.plugins.toolkit.add_resource()` function to
   register your assets directory with CKAN. Edit the ``update_config()``
   method in your ``plugin.py`` file:

   .. literalinclude:: /../ckanext/example_theme_docs/v15_fanstatic/plugin.py
      :pyobject: ExampleThemePlugin.update_config

3. Finally, edit your extension's ``templates/base.html`` file and use CKAN's
   custom Jinja2 tag ``{% asset %}`` instead of the normal ``<link>`` tag to
   import the file:

   .. literalinclude:: /../ckanext/example_theme_docs/v15_fanstatic/templates/base.html
      :language: django

.. note::

  You can put ``{% asset %}`` tags anywhere in any template, and
  Webassets will insert the necessary ``<style>`` and ``<script>``
  tags to include your CSS and |javascript| files. But the best place
  for related asset types is corresponding ``styles`` and ``scripts``
  Jinja2's block.

  Assets will *not* be included on the line where the ``{% asset %}``
  tag is.

.. note::

  A config file *must* be used to configure how Webassets should serve
  each asset file (whether or not to bundle files, what order to
  include files in, whether to include files at the top or bottom of
  the page, dependencies between files, etc.) See
  :doc:`/contributing/frontend/assets` for details.


.. _x-sendfile:

X-Sendfile
^^^^^^^^^^

For web servers which support the *X-Sendfile* feature, you can set
``ckan.webassets.use_x_sendfile`` config option to ``true`` and
configure the web server (eg `Nginx
<https://www.nginx.com/resources/wiki/start/topics/examples/xsendfile/>`_)
in order to serve static files in a more efficient way. Static files
served under the URI ``/webassets/<PATH_TO_STATIC_FILE>`` are stored
in the file system under the path specified by :ref:`ckan.webassets.path` the config
option. If ``ckan.webassets.path`` is not specified, static files are
stored inside a ``webassests`` folder defined by the :ref:`ckan.storage_path` config option.
