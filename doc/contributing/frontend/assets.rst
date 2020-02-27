======
Assets
======

.. Note:: Assets are only supported  on CKAN 2.9 and above. If you
          are using CKAN <= 2.8, refer to the legacy `Fanstatic resources
          <https://docs.ckan.org/en/2.8/contributing/frontend/resources.html>`_
          documentation.

Assets are .css and .js files that may be included in an html page.
Assets are included in the page by using the ``{% asset %}`` tag. CKAN then
uses `Webassets <https://webassets.readthedocs.io/en/latest/>`_ to serve these assets.

::

 {% asset 'library_name/asset_name' %}

Assets are grouped into libraries and the full asset name consists of
``<library name>/<asset name>``. For example:

::

 {% asset 'my_webassets_library/my_javascript_file.js' %}

It is important to note that these assets will be added to the page as
defined by the assets configuration, not in the location of the ``{% asset %}`` tag.
Duplicate assets will not be added and any dependencies will be included as
well as the assets, all in the correct order (see below for details).

Extensions can add new libraries to CKAN using a helper function defined in 
the :doc:` plugins-toolkit <plugins-toolkit>`. See below.

In debug mode assets are served un-minified and un-bundled (ie each asset is
served separately). In non-debug mode the files are served minified and bundled
(where allowed).

.. Note::
    When adding js and css files to the repository, they should be supplied as un-minified files. Minified
    files will be created automatically when serving them.

Assets within extensions
------------------------

To add an asset from an extension, use the ``add_resource(path, name)`` function:

::

 ckan.plugins.toolkit.add_resource('path/to/my/webassets/library/dir',
        'my_webassets_library')

The first argument is the path to the asset directory relative to
the file calling the function (generally ``plugin.py``). The second argument, 
is the name of the library (to be used by templates when they want to
include an asset from the library using the ``{% asset %}`` tag as, so for instance
``my_webassets_library`` in the example shown above).

webassets.yml
-------------

The ``webassets.yml`` file is used to define the assets in a directory and its sub-folders.
Here is an example file. Each section is described below

::

    # Example webassets.yml file

    select2-css:
      contents:
        - select2/select2.css
      output: my_webassets_library/%(version)s_select2.css
      filters: cssrewrite

    jquery:
      contents:
        - jquery.js
      filters: rjsmin
      output: my_webassets_library/%(version)s_jquery.js

    vendor:
      contents:
        - jed.js
        - moment-with-locales.js
        - select2/select2.js
      filters: rjsmin
      output: my_webassets_library/%(version)s_vendor.js
      extra:
        preload:
          - my_webassets_library/select2-css
          - my_webassets_library/jquery

Top level items
~~~~~~~~~~~~~~~

These are names of the available assets

**select2-css**

This asset should be added via ``{% asset 'my_webassets_library/select2-css' %}``.

**jquery**

This asset should be added via ``{% asset 'my_webassets_library/jquery' %}``.

**vendor**

This asset should be added via ``{% asset 'my_webassets_library/vendor' %}``. If it is present in the template, **select2-css** and **jquery** can be omitted (because they are
explicitly defined in ``vendor.extra.preload``)

[contents] (required)
~~~~~~~~~~~~~~~~~~~~~

List of relative paths to source files that will be used to generate
final asset.

.. Important:: An asset *must* only include files of the same
               type. I.e, one cannot mix JS and CSS files in the same
               asset.


[output] (optional)
~~~~~~~~~~~~~~~~~~~

Assets will be compiled the first time they are included in a template.
Output files are located either on the path specified by the ``ckan.webassets.path`` config directive or
at ``{{ ckan.storage_path }}/webassets`` if the former is not provided.
The file specified by the **output** option will be created there. If it's not provided, the file
will be created in a ``webassets-external`` sub-folder. The ``%(version)s`` fragment is a dynamic part that will be replaced with a hash
of the generated file content. This technique is useful to address a number of cache issues for static files.

[filters] (optional)
~~~~~~~~~~~~~~~~~~~~

These are the pre-processors that are applied to the file before producing the final
asset. ``cssrewrite`` for CSS and ``rjsmin`` for JS are
supported out of the box. Details and other options can be found in the `Webassets
documentation
<https://webassets.readthedocs.io/en/latest/builtin_filters.html>`_

[extra] (optional)
~~~~~~~~~~~~~~~~~~

Additional configuration details. Currently, only one option is
supported: ``preload``.

**preload**

Defines list of assets in format ``asset_library/asset_name``, that
must be included into HTML output *before* the current asset.
