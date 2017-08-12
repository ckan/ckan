===============
Extending guide
===============

The following sections will teach you how to customize and extend CKAN's
features by developing your own CKAN extensions.

.. seealso::

    Some **core extensions** come packaged with CKAN. Core extensions don't
    need to be installed before you can use them as they're installed when you
    install CKAN, they can simply be enabled by following the setup
    instructions in each extension's documentation (some core extensions are
    already enabled by default). For example, the :doc:`datastore extension
    </maintaining/datastore>`, :doc:`multilingual extension
    </maintaining/multilingual>`, and :doc:`stats extension
    </maintaining/stats>` are all core extensions, and the :doc:`data viewer
    </maintaining/data-viewer>` also uses core extensions to enable data
    previews for different file formats.

.. seealso::

    **External extensions** are CKAN extensions that don't come packaged with
    CKAN, but must be downloaded and installed separately. A good place to find
    external extensions is the `list of extensions on the CKAN wiki
    <https://github.com/okfn/ckan/wiki/List-of-extensions>`_.  Again, follow
    each extension's own documentation to install, setup and use the extension.

.. toctree::
   :maxdepth: 2

   tutorial
   custom-config-settings
   remote-config-update
   testing-extensions
   best-practices
   adding-custom-fields
   plugin-interfaces
   plugins-toolkit
   validators
   translating-extensions
   flask-migration
