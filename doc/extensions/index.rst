=======================
Writing CKAN extensions
=======================

CKAN can be modified and extended using extensions. Some **core extensions**
come packaged with CKAN. Core extensions don't need to be installed before you
can use them as they're installed when you install CKAN, they can simply be
enabled by following the setup instructions in each extension's documentation
(some core extensions are already enabled by default). For example, the
:doc:`datastore extension </datastore>`, :doc:`multilingual extension
</multilingual>`, and :doc:`stats extension </stats>` are all core extensions,
and the :doc:`data viewer </data-viewer>` also uses core extensions to enable
data previews for different file formats.

**External extensions** are CKAN extensions that don't come packaged with
CKAN, but must be downloaded and installed separately. A good place to find
external extensions is the
`list of extensions on the CKAN wiki <https://github.com/ckan/ckan/wiki/List-of-extensions>`_.
Again, follow each extension's own documentation to install, setup and use the
extension.

This document covers everything you need to know to write your own CKAN
extensions.

.. toctree::
   :maxdepth: 2

   tutorial
   testing-extensions
   best-practices
   plugin-interfaces
   plugins-toolkit
   converters
   validators
