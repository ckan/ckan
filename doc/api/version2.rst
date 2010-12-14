.. toctree::
   :hidden:

.. include:: title.rst.inc
.. include:: purpose.rst.inc
.. include:: overview.rst.inc
.. include:: interfaces2.rst.inc
.. include:: location.rst.inc

Model API
---------

.. include:: model_preamble.rst.inc
.. include:: model_resources.rst.inc
.. include:: model_methods.rst.inc
.. include:: model_formats.rst.inc

Search API
----------

.. include:: search_preamble.rst.inc
.. include:: search_resources.rst.inc
.. include:: search_methods.rst.inc
.. include:: search_formats.rst.inc

Form API
--------

.. include:: form_preamble.rst.inc
.. include:: form_resources.rst.inc
.. include:: form_methods.rst.inc
.. include:: form_formats.rst.inc

.. include:: bottom.rst.inc

Util API
--------

Some of CKAN's client-side Javascript code makes calls to the CKAN API. For
example, to generate a suggestion for a package name when adding a new package
the following API call is made:

::

    /api/2/util/package/create_slug?title=Package+1+Title+Typed+So+Far

The return value is a JSON data structure:

::

    {"valid": true, "name": "package_1_title_typed_so_far"}

These are the keys returned:

``valid`` 

    Can be ``True`` or ``False``. It is ``true`` when the title entered can be
    successfully turned into a package name and when that package name is not
    already being used. It is ``false`` otherwise.

``name``

    The suggested name for the package, based on the title

You can also add ``callback=callback`` to have the response returned as JSONP. eg:

This URL:

::

    /api/2/util/package/create_slug?title=Package+1+Title+Typed+So+Far&callback=callback

Returns:

::

    callback({"valid": true, "name": "package_1_title_typed_so_far"});

In some CKAN deployments you may have the API deployed at a different domain
from the main CKAN code. In these circumstances you'll need to add a new option
to the config file to tell the new package form where it should make its API
requests to:

::

    ckan.api_url = http://api.example.com/


There is also an autocomplete API for tags which looks like this:

This URL:

::

    /api/2/util/tag/autocomplete?incomplete=ru

Returns:

::

    {"ResultSet": {"Result": [{"Name": "russian"}]}}



.. |site| replace:: CKAN
.. |api| replace:: API
.. |version| replace:: Version 2
.. |base_location| replace:: ``http://ckan.net/api/2``
.. |main_doc| replace:: :doc:`../api`
.. |usage| replace:: to view and change

.. |format-package-ref| replace:: Package-Id
.. |format-group-ref| replace:: Group-Id

