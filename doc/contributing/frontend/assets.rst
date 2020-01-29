======
Assets
======

.. Note:: Assets are only supported in the CKAN 2.9 and above. If you
          are using CKAN <= 2.8, refer to legacy `Fanstatic resources
          <https://docs.ckan.org/en/2.8/contributing/frontend/resources.html>`_
          documentation.

Assets are .css and .js files that may be included in an html page.
Assets are included in the page by using the ``{% asset %}`` tag and
CKAN uses `Webassets <https://webassets.readthedocs.io/en/latest/>`_
to serve these assets.

::

 {% asset 'library_name/asset_name' %}

Assets are grouped into libraries and the full asset name consists of
``<library name>/<asset name>``. For example:

::

 {% asset 'my_webassets_library/my_javascript_file.js' %}

It is important to note that these assets will be added to the page as
defined by the assets, not in the location of the ``{% asset %}`` tag.
Duplicate assets will not be added and any dependencies will be included as
well as the assets, all in the correct order (see below for details).

Libraries can be added to CKAN from extensions using a helper function
within the toolkit. See below.

In debug mode assets are served un-minified and unbundled (each asset is
served separately). In non-debug mode the files are served minified and bundled
(where allowed).

.. Note::
    .js and .css assets should be supplied as un-minified files.  Minified
    files will be created(if configured).

Assets within extensions
---------------------------

To add a asset within a extension helper function ``add_resource(path, name)``:

::

 ckan.plugins.toolkit.add_resource('path/to/my/webassets/library/dir',
        'my_webassets_library')

The first argument, ``path``, is the path to the asset directory relative to
the file calling the function. The second argument, ``name`` is the name of the
library (to be used by templates when they want to include a asset from the
library using the ``{% asset %}`` tag as shown above).

webassets.yml
-------------

This file is used to define the assets in a directory and its sub folders.
Here is an example file.
::

    # Example webassets.yml file

    select2-css:
      output: my_webassets_library/%(version)s_select2.css
      filters: cssrewrite
      contents:
        - select2/select2.css

    jquery:
      filters: rjsmin
      output: my_webassets_library/%(version)s_jquery.js
      contents:
        - jquery.js

    vendor:
      filters: rjsmin
      output: my_webassets_library/%(version)s_vendor.js
      extra:
        preload:
          - my_webassets_library/select2-css
          - my_webassets_library/jquery
      contents:
        - jed.js
        - moment-with-locales.js
        - select2/select2.js

Top level items
~~~~~~~~~~~~~~~

Those are names of available assets

**select2-css**

This asset should be added via ``{% asset 'my_webassets_library/select2-css' %}``.

**jquery**

This asset should be added via ``{% asset 'my_webassets_library/jquery' %}``.

**vendor**

This asset should be added via ``{% asset
'my_webassets_library/vendor' %}``. If it present in the template,
**select2-css** and **jquery** may be omitted(because they are
explicitly mentioned at ``vendor.extra.preload``)


[output] (optional)
~~~~~~~~~~~~~~~~~~~

Assets will be compiled at the first time they are included into
template. Output files are located either at path specified by
``ckan.webassets.path`` config directive or at ``ckan.storage_path`` /
``webassets`` if former is not provided. Under this path will be
created file, specified by **output** option. If it not provided, file
goes to ``webassets-external`` sub-folder. ``%(version)s``
fragment(optional) is a dynamic part that will be replaced with hash
of generated file content - this technique solves a number of cache
issues for static files.

[filters] (optional)
~~~~~~~~~~~~~~~~~~~~

Preprocessors that are applied to file before producing final
asset. Out of the box ``cssrewrite`` for CSS and ``rjsmin`` for JS are
supported. Details and other options can be found in `Webassets
documentation
<https://webassets.readthedocs.io/en/latest/builtin_filters.html>`_

[extra] (optional)
~~~~~~~~~~~~~~~~~~

Additional configuration details. Currently, only one option is
supported: ``preload``.

**preload**

Defines list of assets in format ``asset_library/asset_name``, that
must be included into HTML output *before* current asset.

[contents] (required)
~~~~~~~~~~~~~~~~~~~~~

List of relative paths to source files that will be used to generate
final asset.

.. Important:: Asset *must* be composed using only files of the same
               type. I.e, one cannot mix JS and CSS files in single
               asset.
