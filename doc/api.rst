.. _action-api:

The CKAN API v3
===============

All of a CKAN website's core functionality (everything you can do with the web
interface and more) can be used by code via CKAN's API (Application Programming
Interface). For example, using the CKAN API your program can:

* Get a list of all a site's datasets, resources or other CKAN objects
* Get the details of a particular dataset, resource or other object
* Search for packages or resources matching a query
* Create, update and delete datasets, resources and other objects
* Get an activity stream of recently changed datasets on a site

The API calls the same internal functions that are used by the web interface,
so it exposes the full set of read and write operations and all their
parameters.


Making an API Request
---------------------

To call the CKAN API, post a JSON dictionary in an HTTP POST request to one of
CKAN's API URLs. The parameters for the API function should be given in the
JSON dictionary. CKAN will also return its response in a JSON dictionary.

One way to post a JSON dictionary to a URL is using the command-line HTTP
client `HTTPie <http://httpie.org/>`_.  For example, to get a list of the names
of all the datasets in the ``data-explorer`` group on demo.ckan.org, install
HTTPie and then call the ``group_list`` API function by running this command
in a terminal::

    http http://demo.ckan.org/api/action/group_list id=data-explorer

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

1. ``"sucess"``: ``true`` or ``false``.

   The API aims to always return ``200 OK`` as the status code of its HTTP
   response, whether there were errors with the request or not, so it's
   important to always check the value of the ``"success"`` key in the response
   dictionary and (if success is ``False``) check the value of the ``"error"``
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

    # Use the json module to dump a dictionary to a string for posting.
    data_string = urllib.quote(json.dumps({'id': 'data-explorer'}))

    # Make the HTTP request.
    response = urllib2.urlopen('http://demo.ckan.org/api/action/group_list',
            data_string)

    # Use the json module to load CKAN's response into a dictionary.
    response_dict = json.loads(response.read())

    # Check the contents of the response.
    assert response_dict['success'] is True
    result = response_dict['result']
    pprint.pprint(result)


Making an API Request with No Parameters
----------------------------------------

If the API function you're calling doesn't require any parameters, you still
need to post an empty dictionary. For example, with HTTPie::

    http http://demo.ckan.org/api/action/package_list body=''

Or, in Python::

    response = urllib2.urlopen(
        'http://demo.ckan.org/api/action/group_list', '{}')


Authentication and API Keys
---------------------------

Some API functions require authorization. The API uses the same authorization
functions and configuration as the web interface, so if a user is authorized to
do something in the web interface they'll be authorized to do it via the API as
well.

When calling an API function that requires authorization, you must authenticate
yourself by providing your API key with your HTTP request. To find your API
key, login to the CKAN site using its web interface and visit your user profile
page.

To provide your API key in an HTTP request, include it in either an
``Authorization`` or ``X-CKAN-API-Key`` header.  (The name of the HTTP header
can be configured with the ``apikey_header_name`` option in your CKAN
configuration file.)

For example, to ask whether or not you're currently following the user
``markw`` on demo.ckan.org using HTTPie, run this command::

    http http://demo.ckan.org/api/action/am_following_user id=markw Authorization:XXX

(Replacing ``XXX`` with your API key.)

Or, to get the list of activities from your user dashboard on demo.ckan.org,
run this Python code::

    request = urllib2.Request('http://demo.ckan.org/api/action/dashboard_activity_list')
    request.add_header('Authorization', 'XXX')
    response_dict = json.loads(urllib2.urlopen(request, '{}').read())


GET-able API Functions
----------------------

Functions defined in `ckan.logic.action.get`_ can also be called with an HTTP
GET request.  For example, to search for datasets (packages) matching the
search query ``spending``, on demo.ckan.org, open this URL in your browser::

http://demo.ckan.org/api/action/package_search?q=spending

.. tip::

 Browser plugins like `JSONView for Firefox <https://addons.mozilla.org/en-us/firefox/addon/jsonview/>`_
 or `Chrome <https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc>`_
 will format and color CKAN's JSON response nicely in your browser.

The search query is given as a URL parameter ``?q=spending``. Multiple
URL parameters can be appended, separated by ``&`` characters, for example
to get only the first 10 matching datasets open this URL::

http://demo.ckan.org/api/action/package_search?q=spending&rows=10

When an action requires a list of strings as the value of a parameter, the
value can be sent by giving the parameter multiple times in the URL::

http://demo.ckan.org/api/action/term_translation_show?terms=russian&terms=romantic%20novel

If the action you're calling doesn't require any parameters, you still need
to add a fake parameter to the URL. For example to get a list of all
datasets on demo.ckan.org::

http://demo.ckan.org/api/action/package_list?foo


JSONP Support
-------------

To cater for scripts from other sites that wish to access the API, the data can
be returned in JSONP format, where the JSON data is 'padded' with a function
call. The function is named in the 'callback' parameter. For example::

http://demo.ckan.org/api/action/package_show?id=adur_district_spending&callback=myfunction

.. todo :: This doesn't work with all functions.

.. _api-reference: 

API v3 Reference
----------------


ckan.logic.action.get
`````````````````````

.. automodule:: ckan.logic.action.get
   :members:


ckan.logic.action.create
````````````````````````

.. automodule:: ckan.logic.action.create
   :members:


ckan.logic.action.update
````````````````````````

.. automodule:: ckan.logic.action.update
   :members:


ckan.logic.action.delete
````````````````````````

.. automodule:: ckan.logic.action.delete
   :members:
