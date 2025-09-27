Creating dynamic user interfaces with htmx
==========================================

Starting version 2.11, CKAN is shipped with `htmx <https://htmx.org/>`_.

    *"htmx gives you access to AJAX, CSS Transitions, WebSockets and Server Sent
    Events directly in HTML, using attributes, so you can build modern user
    interfaces with the simplicity and power of hypertext."*
    -- `htmx.org <https://htmx.org/>`_

While not all CKAN templates have been updated to use ``htmx``, you can use it
in your own extensions to build modern user interfaces. htmx will be the core
component in the implementation of the new CKAN UI, so you should expect more
of it in future versions.

--------
Overview
--------

``htmx`` is a library that allows you to use HTML attributes to make AJAX requests
and update the DOM. It is a great alternative to Javascript frameworks like
React or Vue, as it allows you to build dynamic user interfaces with regular flask
views and Jinja2 templates, allowing templates to be overridden by themes and other extensions.

The library is very simple to use. You just need to add the ``hx-*`` attributes
to your HTML elements to make them dynamic. For example, to make a link that
makes a POST request to the ``/dataset/follow/<dataset-id>`` endpoint and
replaces the HTML element with id ``package-info`` with all the HTML returned by
the endpoint, you can write:

.. code-block:: jinja

    <a class="btn btn-danger" hx-post="{{ h.url_for('dataset.follow', id=pkg.id) }}" hx-target="#package-info">
      <i class="fa-solid fa-circle-plus"></i>
      Follow
    </a>

The example can be read as: "When the user clicks on this link, make a POST request to the
``/dataset/follow/<dataset-id>`` endpoint and replace the HTML element with id
``package-info`` with all the HTML returned by the endpoint". Notice how we are using the
``hx-post`` and ``hx-target`` attributes to define the behaviour of the link.

For a full list of the HTML attributes and their usage, check the `htmx documentation <https://htmx.org/reference/>`_.


-----------------------------------
Implementing new features with htmx
-----------------------------------

``htmx`` give us the flexibility to implement new dynamic features in CKAN by implementing
new endpoints that returns the partial HTML that we want to insert into the page. The
**Follow** / **Unfollow** logic is a great example of this and we will explain the thought
process behind it in this section.

In UI terms, the **Follow** / **Unfollow** logic is just a div containing a button that
allows the user to follow/unfollow a dataset plus a counter that shows the number of
followers. The div is displayed in the dataset page.

This is a small interactive action and we do not want a typical full refresh of the page. It
doesn't make any sense to reload the whole page just to update the number of followers and the
button. This is a perfect use case for ``htmx``.

What we need to achieve this behaviour is:
  1. A HTML structure that encapsulates the follow/unfollow UI in a single HTML element (so it can be replaced).
  2. A way to trigger a call to the endpoint when the user clicks on the button and replace the element with the new content.
  3. A new endpoint that covers the backed logic and returns just enough HTML to replace the HTML element.


1. HTML structure

The HTML structure is very simple: an element that contains the button and the counter.
To respect the current CKAN UX we update the ``package/snippets/info.html`` snippet.
We need to make sure that the ``section`` HTML element we want to replace has an id so
we add it: ``id="package-info"``.

.. code-block:: jinja

    <!-- package/snippets/info.html -->
    {% block package_info %}
      {% if pkg %}
        <section id="package-info" class="module module-narrow">
        <!-- Rest of the snippet -->
        </section>
      {% endif %}
    {% endblock %}


2. Triggering a call to the endpoint

We need to trigger a call to the endpoint when the user clicks on the button. We can do this by adding the
``hx-post`` attribute to the button. The ``hx-post`` attribute defines the URL that will be called when the
user clicks on the button. In our case, we want to call the ``/dataset/follow/<dataset-id>`` endpoint, so
we can use the ``h.url_for`` helper to generate the URL.


.. code-block:: jinja

    <a class="btn btn-danger" hx-post="{{ h.url_for('dataset.follow', id=pkg.id) }}" hx-target="#package-info">
      <i class="fa-solid fa-circle-plus"></i>
      Follow
    </a>

In addition to the ``hx-post`` attribute, we also need to define the ``hx-target`` attribute. The ``hx-target``
attribute defines the HTML element that will be replaced with the HTML returned by the endpoint. In our case,
we want to replace the ``package-info`` element, so we can use the ``#package-info`` selector.

3. The endpoint

The last step is to implement the endpoint that will be called when the user clicks on the button. In our case,
we want to call the ``/dataset/follow/<dataset-id>`` endpoint. This endpoint is already implemented in CKAN.
We need to make sure that, under this new context, it should return only the partial HTML that we want to insert into the page
instead of rendering the whole dataset page again.  We achieve that by making it sure that we return the snippet that
contains the HTML that we want to display, in our case ``package/snippets/info.html``.

View:

.. literalinclude:: ../../ckan/views/dataset.py
    :pyobject: follow


Note that this endpoint is reusing the ``package/snippets/info.html`` that is also being called in
``package/read_base.html`` when calling ``/dataset/<dataset-id>``. This shows how modular and reusable the CKAN
templates are with ``htmx``.

-------------------------------------------
2. Accessing to HTMX request headers in CKAN
-------------------------------------------

CKAN adds a new property to the CKANRequest class called ``htmx`` that you can
use to access the htmx request headers. For example::

    from ckan.common import request

    if request.htmx:
        # do something


Calling ``request.htmx`` will return a HtmxDetails object that contains attributes
for each one of the ``htmx`` attributes. For example, if you want to access the
``hx-target`` attribute, you can write::

    from ckan.common import request

    if request.htmx:
        target = request.htmx.target

.. literalinclude:: ../../ckan/common.py
    :pyobject: HtmxDetails


----------------
3. htmx examples
----------------

Check the `htmx examples <https://htmx.org/examples/>`_ for an
overview of patterns that you can use to implement rich UX features.
