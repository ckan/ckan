The FileStore API
=================

CKAN's FileStore API lets you upload files to CKAN's
:doc:`FileStore <filestore>`. If you're looking for an example,
`ckanclient <https://github.com/okfn/ckanclient>`_ contains
`Python code for uploading a file to CKAN using the FileStore API <https://github.com/okfn/ckanclient/blob/master/ckanclient/__init__.py#L546>`_.


FileStore Metadata API
----------------------

The API is located at::

     /api/storage/metadata/{label}

It supports the following methods:

* GET will return the metadata
* POST will add/update metadata
* PUT will replace metadata

Metadata is a json dict of key values which for POST and PUT should be send in body of request.

A standard response looks like::

    {
      "_bucket": "ckannet-storage",
      _content_length: 1074
      _format: "text/plain"
      _label: "/file/8630a664-0ae4-485f-99c2-126dae95653a"
      _last_modified: "Fri, 29 Apr 2011 19:27:31 GMT"
      _location: "some-location"
      _owner: null
      uploaded-by: "bff737ef-b84c-4519-914c-b4285144d8e6"
    }

Note that values with '_' are standard OFS metadata and are mostly read-only -- _format i.e. content-type can be set).


FileStore Form Authentication API
---------------------------------

Provides credentials for doing operations on storage directly from a client
(using web form style POSTs).

The API is located at::

    /api/storage/auth/form/{label}

Provide fields for a form upload to storage including authentication::

    :param label: label.
    :return: json-encoded dictionary with action parameter and fields list.


FileStore Request Authentication API
------------------------------------

Provides credentials for doing operations on storage directly from a client.

.. warning:: This API is currently disabled and will likely be deprecated.
             Use the form authentication instead.

The API is at::

    /api/storage/auth/request/{label}

Provide authentication information for a request so a client can
interact with backend storage directly::

    :param label: label.
    :param kwargs: sent either via query string for GET or json-encoded
        dict for POST). Interpreted as http headers for request plus an
        (optional) method parameter (being the HTTP method).

        Examples of headers are:

            Content-Type
            Content-Encoding (optional)
            Content-Length
            Content-MD5
            Expect (should be '100-Continue')

    :return: is a json hash containing various attributes including a
    headers dictionary containing an Authorization field which is good for
    15m.
