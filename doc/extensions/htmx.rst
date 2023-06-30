htmx
====

Starting version 2.11, CKAN is shipped with `htmx <https://htmx.org/>`_.

    *"htmx gives you access to AJAX, CSS Transitions, WebSockets and Server Sent
    Events directly in HTML, using attributes, so you can build modern user
    interfaces with the simplicity and power of hypertext."*
    -- `htmx.org <https://htmx.org/>`_

While not all CKAN templates have been updated to use htmx, you can use it
in your own extensions to build modern user interfaces. htmx will be the core
component in the implementation of the new CKAN UI, so you should expect more
of it in future versions.

---------
1. Usage
---------

CKAN adds a new property to the CKANRequest class called `htmx` that you can
use to access the htmx request headers. For example::

    from ckan.common import request

    if request.htmx:
        # do something


`request.htmx` will return a HtmxDetails object:

.. literalinclude:: ../../ckan/common.py
    :pyobject: HtmxDetails
