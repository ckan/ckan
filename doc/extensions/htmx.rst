Creating dynamic user interfaces with htmx
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

CKAN adds a new property to the CKANRequest class called ``htmx`` that you can
use to access the htmx request headers. For example::

    from ckan.common import request

    if request.htmx:
        # do something


``request.htmx`` will return a ``HtmxDetails`` object:

.. literalinclude:: ../../ckan/common.py
    :pyobject: HtmxDetails

To make a request using htmx, you can use the ``hx-*`` html properties defined by
the library. Check the `htmx examples <https://htmx.org/examples/>`_ for an
overview of patterns and uses.

----------------
2. htmx in CKAN
----------------

For an exaple of how we are using htmx in CKAN, check the **Follow** / **Unfollow**
logic.

The **Follow** button is a simple link that makes a POST request to the
``/dataset/follow/<dataset-id>`` and then replaces the section ``package-info`` with
all the HTML returned by the endpoint.


.. code-block:: jinja

    <a class="btn btn-danger" hx-post="{{ h.url_for('dataset.unfollow', id=group.id) }}" hx-target="#package-info">
      <i class="fa-solid fa-circle-minus"></i>
      Unfollow
    </a>


This endpoint is reusing the ``package/snippets/info.html`` that is called in
``package/read_base.html`` to render the dataset info in the dataset page when calling
``/dataset/<dataset-id>``.

Snippet:

.. literalinclude:: ../../ckan/templates/package/snippets/info.html
    :language: html

View:

.. literalinclude:: ../../ckan/views/dataset.py
    :pyobject: follow

