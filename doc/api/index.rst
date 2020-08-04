.. _action api:

=========
API guide
=========

This section documents CKAN's API, for developers who want to write code that
interacts with CKAN sites and their data.

CKAN's **Action API** is a powerful, RPC-style API that exposes all of CKAN's
core features to API clients. All of a CKAN website's core functionality
(everything you can do with the web interface and more) can be used by external
code that calls the CKAN API.  For example, using the CKAN API your app can:

* Get JSON-formatted lists of a site's datasets, groups or other CKAN objects:

  http://demo.ckan.org/api/3/action/package_list

  http://demo.ckan.org/api/3/action/group_list

  http://demo.ckan.org/api/3/action/tag_list

* Get a full JSON representation of a dataset, resource or other object:

  http://demo.ckan.org/api/3/action/package_show?id=adur_district_spending

  http://demo.ckan.org/api/3/action/tag_show?id=gold

  http://demo.ckan.org/api/3/action/group_show?id=data-explorer

* Search for packages or resources matching a query:

  http://demo.ckan.org/api/3/action/package_search?q=spending

  http://demo.ckan.org/api/3/action/resource_search?query=name:District%20Names

* Create, update and delete datasets, resources and other objects

* Get an activity stream of recently changed datasets on a site:

  http://demo.ckan.org/api/3/action/recently_changed_packages_activity_list

.. note::

   CKAN's FileStore and DataStore have their own APIs, see:

   * :doc:`/maintaining/filestore`
   * :doc:`/maintaining/datastore`

.. note::

   For documentation of CKAN's legacy API's, see :doc:`legacy-api`.

.. We put legacy-api in a hidden toctree here just so that Sphinx gets the
   links in the sidebar right when on the legacy-api page.

.. toctree::
   :hidden:

   legacy-api


.. note:: On early CKAN versions, datasets were called "packages" and this name
    has stuck in some places, specially internally and on API calls. Package has
    exactly the same meaning as "dataset".


---------------------
Making an API request
---------------------

To call the CKAN API, post a JSON dictionary in an HTTP POST request to one of
CKAN's API URLs. The parameters for the API function should be given in the
JSON dictionary. CKAN will also return its response in a JSON dictionary.

One way to post a JSON dictionary to a URL is using the command-line
client `Curl <https://curl.haxx.se/>`_.  For example, to get a list of the names
of all the datasets in the ``data-explorer`` group on demo.ckan.org, install
curl and then call the ``group_list`` API function by running this command
in a terminal::

    curl https://demo.ckan.org/api/3/action/group_list

The response from CKAN will look like this::

    {
        "help": "...",
        "result": [
            "data-explorer",
            "department-of-ricky",
            "geo-examples",
            "geothermal-data",
            "reykjavik",
            "skeenawild-conservation-trust"
        ],
        "success": true
    }

The response is a JSON dictionary with three keys:

1. ``"success"``: ``true`` or ``false``.

   The API aims to always return ``200 OK`` as the status code of its HTTP
   response, whether there were errors with the request or not, so it's
   important to always check the value of the ``"success"`` key in the response
   dictionary and (if success is ``false``) check the value of the ``"error"``
   key.

.. note::

    If there are major formatting problems with a request to the API, CKAN
    may still return an HTTP response with a ``409``, ``400`` or ``500``
    status code (in increasing order of severity). In future CKAN versions
    we intend to remove these responses, and instead send a ``200 OK``
    response and use the ``"success"`` and ``"error"`` items.

2. ``"result"``: the returned result from the function you called. The type
   and value of the result depend on which function you called. In the case of
   the ``group_list`` function it's a list of strings, the names of all the
   datasets that belong to the group.

   If there was an error responding to your request, the dictionary will
   contain an ``"error"`` key with details of the error instead of the
   ``"result"`` key. A response dictionary containing an error will look like
   this::

       {
           "help": "Creates a package",
           "success": false,
           "error": {
               "message": "Access denied",
               "__type": "Authorization Error"
               }
        }

3. ``"help"``: the documentation string for the function you called.

The same HTTP request can be made using Python's standard ``urllib2`` module,
with this Python code::

    #!/usr/bin/env python
    import urllib2
    import urllib
    import json
    import pprint

    # Make the HTTP request.
    response = urllib2.urlopen('http://demo.ckan.org/api/3/action/group_list',
            data_string)
    assert response.code == 200

    # Use the json module to load CKAN's response into a dictionary.
    response_dict = json.loads(response.read())

    # Check the contents of the response.
    assert response_dict['success'] is True
    result = response_dict['result']
    pprint.pprint(result)


---------------------------------------------
Example: Importing datasets with the CKAN API
---------------------------------------------

You can add datasets using CKAN's web interface, but when importing many
datasets it's usually more efficient to automate the process in some way.  In
this example, we'll show you how to use the CKAN API to write a Python script
to import datasets into CKAN.

.. todo::

   Make this script more interesting (eg. read data from a CSV file), and all
   put the script in a .py file somewhere with tests and import it here.

::

    #!/usr/bin/env python
    import urllib2
    import urllib
    import json
    import pprint

    # Put the details of the dataset we're going to create into a dict.
    dataset_dict = {
        'name': 'my_dataset_name',
        'notes': 'A long description of my dataset',
        'owner_org': 'org_id_or_name'
    }

    # Use the json module to dump the dictionary to a string for posting.
    data_string = urllib.quote(json.dumps(dataset_dict))

    # We'll use the package_create function to create a new dataset.
    request = urllib2.Request(
        'http://www.my_ckan_site.com/api/action/package_create')

    # Creating a dataset requires an authorization header.
    # Replace *** with your API key, from your user account on the CKAN site
    # that you're creating the dataset on.
    request.add_header('Authorization', '***')

    # Make the HTTP request.
    response = urllib2.urlopen(request, data_string)
    assert response.code == 200

    # Use the json module to load CKAN's response into a dictionary.
    response_dict = json.loads(response.read())
    assert response_dict['success'] is True

    # package_create returns the created package as its result.
    created_package = response_dict['result']
    pprint.pprint(created_package)

For more examples, see :ref:`api-examples`.



------------
API versions
------------

The CKAN APIs are versioned. If you make a request to an API URL without a
version number, CKAN will choose the latest version of the API::

    http://demo.ckan.org/api/action/package_list

Alternatively, you can specify the desired API version number in the URL that
you request::

    http://demo.ckan.org/api/3/action/package_list

Version 3 is currently the only version of the Action API.

We recommend that you specify the API number in your requests, because this
ensures that your API client will work across different sites running different
version of CKAN (and will keep working on the same sites, when those sites
upgrade to new versions of CKAN). Because the latest version of the API may
change when a site is upgraded to a new version of CKAN, or may differ on
different sites running different versions of CKAN, the result of an API
request that doesn't specify the API version number cannot be relied on.


.. _api authentication:

-----------------------------
Authentication and API tokens
-----------------------------

.. warning:: Starting from CKAN 2.9, API tokens are the preferred way of authenticating API calls.
    The old legacy API keys will still work but they will be removed in future versions so it is
    recommended to switch to use API tokens. Read below for more details.


Some API functions require authorization. The API uses the same authorization
functions and configuration as the web interface, so if a user is authorized to
do something in the web interface they'll be authorized to do it via the API as
well.

When calling an API function that requires authorization, you must
authenticate yourself by providing an authentication key with your
HTTP request. Starting from CKAN 2.9 the recommended mechanism to use are API tokens. These are
encrypted keys that can be generated manually from the UI (User Profile > Manage > API tokens)
or via the :py:func:`~ckan.logic.action.create.api_token_create` function. A user can create as many tokens as needed
for different uses, and revoke one or multiple tokens at any time. In addition, enabling
the ``expire_api_token`` core plugin allows to define the expiration timestamp for a token. 

Site maintainers can use :ref:`config-api-tokens` to configure the token generation.

Legacy API keys (UUIDs that look like `ec5c0860-9e48-41f3-8850-4a7128b18df8`) are still supported,
but its use is discouraged as they are not as secure as tokens and are limited to one per user.
Support for legacy API keys will be removed in future CKAN versions.


To provide your API token in an HTTP request, include it in either an
``Authorization`` or ``X-CKAN-API-Key`` header.  (The name of the HTTP header
can be configured with the ``apikey_header_name`` option in your CKAN
configuration file.)

For example, to ask whether or not you're currently following the user
``markw`` on demo.ckan.org using curl, run this command::

    curl -H "Authorization: XXX"  https://demo.ckan.org/api/3/action/am_following_user?id=markw

(Replacing ``XXX`` with your API token.)

Or, to get the list of activities from your user dashboard on demo.ckan.org,
run this Python code::

    request = urllib2.Request('https://demo.ckan.org/api/3/action/dashboard_activity_list')
    request.add_header('Authorization', 'XXX')
    response_dict = json.loads(urllib2.urlopen(request, '{}').read())


----------------------
GET-able API functions
----------------------

Functions defined in `ckan.logic.action.get`_ can also be called with an HTTP
GET request.  For example, to get the list of datasets (packages) from
demo.ckan.org, open this URL in your browser:

http://demo.ckan.org/api/3/action/package_list

Or, to search for datasets (packages) matching the search query ``spending``,
on demo.ckan.org, open this URL in your browser:

http://demo.ckan.org/api/3/action/package_search?q=spending

.. tip::

 Browser plugins like `JSONView for Firefox <https://addons.mozilla.org/en-us/firefox/addon/jsonview/>`_
 or `Chrome <https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc>`_
 will format and color CKAN's JSON response nicely in your browser.

The search query is given as a URL parameter ``?q=spending``. Multiple
URL parameters can be appended, separated by ``&`` characters, for example
to get only the first 10 matching datasets open this URL:

http://demo.ckan.org/api/3/action/package_search?q=spending&rows=10

When an action requires a list of strings as the value of a parameter, the
value can be sent by giving the parameter multiple times in the URL:

http://demo.ckan.org/api/3/action/term_translation_show?terms=russian&terms=romantic%20novel


-------------
JSONP support
-------------

To cater for scripts from other sites that wish to access the API, the data can
be returned in JSONP format, where the JSON data is 'padded' with a function
call. The function is named in the 'callback' parameter. For example:

http://demo.ckan.org/api/3/action/package_show?id=adur_district_spending&callback=myfunction

.. note :: This only works for GET requests


.. _api-examples:

------------
API Examples
------------


Tags (not in a vocabulary)
==========================

A list of all tags:

* browser: http://demo.ckan.org/api/3/action/tag_list
* curl: ``curl http://demo.ckan.org/api/3/action/tag_list``
* ckanapi: ``ckanapi -r http://demo.ckan.org action tag_list``

Top 10 tags used by datasets:

* browser: http://demo.ckan.org/api/action/package_search?facet.field=[%22tags%22]&facet.limit=10&rows=0
* curl: ``curl 'http://demo.ckan.org/api/action/package_search?facet.field=\["tags"\]&facet.limit=10&rows=0'``
* ckanapi: ``ckanapi -r http://demo.ckan.org action package_search facet.field='["tags"]' facet.limit=10 rows=0``

All datasets that have tag 'economy':

* browser: http://demo.ckan.org/api/3/action/package_search?fq=tags:economy
* curl: ``curl 'http://demo.ckan.org/api/3/action/package_search?fq=tags:economy'``
* ckanapi: ``ckanapi -r http://demo.ckan.org action package_search fq='tags:economy'``

Tag Vocabularies
================

Top 10 tags and vocabulary tags used by datasets:

* browser: http://demo.ckan.org/api/action/package_search?facet.field=[%22tags%22]&facet.limit=10&rows=0
* curl: ``curl 'http://demo.ckan.org/api/action/package_search?facet.field=\["tags"\]&facet.limit=10&rows=0'``
* ckanapi: ``ckanapi -r http://demo.ckan.org action package_search facet.field='["tags"]' facet.limit=10 rows=0``

e.g. Facet: `vocab_Topics` means there is a vocabulary called Topics, and its top tags are listed under it.

A list of datasets using tag 'education' from vocabulary 'Topics':

* browser: https://data.hdx.rwlabs.org/api/3/action/package_search?fq=vocab_Topics:education
* curl: ``curl 'https://data.hdx.rwlabs.org/api/3/action/package_search?fq=vocab_Topics:education'``
* ckanapi: ``ckanapi -r https://data.hdx.rwlabs.org action package_search fq='vocab_Topics:education'``


Uploading a new version of a resource file
==========================================

You can use the ``upload`` parameter of the
:py:func:`~ckan.logic.action.update.resource_update` function to upload a
new version of a resource file. This requires a ``multipart/form-data``
request, with curl you can do this using the ``@file.csv``::

    curl -X POST  -H "Content-Type: multipart/form-data"  -H "Authorization: XXXX"  -F "id=<resource_id>" -F "upload=@updated_file.csv" https://demo.ckan.org/api/3/action/resource_update


.. _api-reference:

--------------------
Action API reference
--------------------

.. note::

   If you call one of the action functions listed below and the function
   raises an exception, the API will return a JSON dictionary with keys
   ``"success": false`` and an ``"error"`` key indicating the exception
   that was raised.

   For example :py:func:`~ckan.logic.action.get.member_list` (which returns a
   list of the members of a group) raises :py:class:`~ckan.logic.NotFound` if
   the group doesn't exist. If you called it over the API, you'd get back a
   JSON dict like this::

    {
        "success": false
        "error": {
            "__type": "Not Found Error",
            "message": "Not found"
        },
        "help": "...",
    }


ckan.logic.action.get
=====================

.. automodule:: ckan.logic.action.get
   :members:

ckan.logic.action.create
========================

.. automodule:: ckan.logic.action.create
   :members:

ckan.logic.action.update
========================

.. automodule:: ckan.logic.action.update
   :members:

ckan.logic.action.patch
=======================

.. versionadded:: 2.3

.. automodule:: ckan.logic.action.patch
   :members:

ckan.logic.action.delete
========================

.. automodule:: ckan.logic.action.delete
   :members:
