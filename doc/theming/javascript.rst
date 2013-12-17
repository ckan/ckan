=============================
Customizing CKAN's JavaScript
=============================

JavaScript code in CKAN is broken down into *modules*: small, independent units
of JavaScript code. CKAN themes can add JavaScript features by providing their
own modules. This tutorial will explain the main concepts involved in CKAN
JavaScript modules and walk you through the process of adding custom modules
to themes.


.. todo:: Link to an introductory JavaScript tutorial and other necessary
          background knowledge.


--------
Overview
--------

The idea behind CKAN's JavaScript modules is to keep the code simple and
easy to test, debug and maintain, by breaking it down into small,
independent modules. JavaScript modules in CKAN don't share global
variables, and don't call each other's code.

These JavaScript modules are attached to HTML elements in the page, and enhance
the functionality of those elements. The idea is that an HTML element with a
JavaScript module attached should still be fully functional even if JavaScript
is completely disabled (e.g. because the user's web browser doesn't support
JavaScript). The user experience may not be quite as nice, but the
functionality should still be there.

.. todo:: Example of graceful degradation.

CKAN makes a few helpful objects and functions available for every JavaScript
module to use, including:

* :js:data:`this.sandbox`, an object containing useful functions for all
  modules to use, including an API client for calling the API
  (:js:data:`this.sandbox.client`) and :ref:`internationalization functions
  <javascript i18n>`.

* The `jQuery library <http://jquery.com/>`_, available to JavaScript modules
  via :js:data:`this.sandbox.jQuery`.

  jQuery provides many useful features in an easy-to-use API, including
  document traversal and manipulation, event handling, and animation. See
  `jQuery's own docs <http://jquery.com/>`_ for details.

* :ref:`Pubsub functions <pubsub>` that modules can use to communicate with
  each other, if they really need to.

* Bootstrap's JavaScript features, see the
  `Bootstrap docs <http://getbootstrap.com/2.3.2/javascript.html>`_
  for details.

.. todo::

   The standard ``window`` object is also available to modules,
   but I'm not sure if we encourage using it, or if CKAN adds anything special
   to it.


In the sections below, we'll walk you through the steps to add a new JavaScript
feature to CKAN - dataset info popovers. We'll add an info button to each
dataset on the datasets page which, when clicked, opens a popover containing
some extra information and user actions related to the dataset.

.. todo:: Insert a screenshot of the finished example.


--------------------------------
Initializing a JavaScript module
--------------------------------

To get CKAN to call some custom JavaScript code, we need to:

1. Implement a |javascript| module, and register it with CKAN.
   Create the file ``ckanext-example_theme/fanstatic/example_theme_popover.js``, with these
   contents:

   .. todo::

      What is the standard way to name the two arguments to the ``module()``
      function? I've seen ``jQuery`` and ``$`` and ``i18n`` and ``_``.

   .. literalinclude:: /../ckanext/example_theme/v16_initialize_a_javascript_module/fanstatic/example_theme_popover.js
      :language: javascript

   .. note::

      |javascript| module names should begin with the name of the extension,
      to avoid conflicting with other modules.
      See :ref:`javascript module names best practice`.

   This bit of |javascript| calls the ``ckan.module()`` function to register a
   new JavaScript module with CKAN. ``ckan.module()`` takes two arguments: the
   name of the module being registered (``'example_theme_popover'`` in this
   example) and a function that returns the module itself. The function takes
   two arguments, which we'll look at later. The module is just a |javascript|
   object with a single attribute, ``initialize``, whose value is a function
   that CKAN will call to initialize the module. In this example, the
   initialize function just prints out a confirmation message - this
   |javascript| module doesn't do anything interesting yet.

   .. note::

      Each |javascript| module's ``initialize()`` function is called on
      `DOM ready <http://api.jquery.com/ready/>`_.

2. Include the |javascript| module in a page, using Fanstatic, and apply it to
   one or more HTML elements on that page. We'll override CKAN's
   ``package_item.html`` template snippet to insert our module whenever a
   package is rendered as part of a list of packages (for example, on the
   dataset search page). Create the file
   ``ckanext-example_theme/templates/snippets/package_item.html`` with these
   contents:

   .. literalinclude:: /../ckanext/example_theme/v16_initialize_a_javascript_module/templates/snippets/package_item.html
      :language: django

   .. todo:: Link to something about HTML data-* attributes.

   If you now restart the development server and open
   http://127.0.0.1:5000/dataset in your web browser, you should see an
   extra info button next to each dataset shown. If you open a
   |javascript| console in your browser, you should see the message that your
   module has printed out.

   .. todo:: Link to something about JavaScript consoles.

   If you have more than one dataset on your page, you'll see the module's
   message printed once for each dataset. The ``package_item.html`` template
   snippet is rendered once for each dataset that's shown in the list, so your
   ``<button>`` element with the ``data-module="example_theme_popover"``
   attribute is rendered once for each dataset, and CKAN creates a new instance
   of your |javascript| module for each of these ``<button>`` elements.  If you
   view the source of your page, however, you'll see that
   ``example_theme_popover.js`` is only included with a ``<script>`` tag once.
   Fanstatic is smart enough to deduplicate resources.

   .. note:: |javascript| modules *must* be included as Fanstatic resources,
      you can't add them to a ``public`` directory and include them using your
      own ``<script>`` tags.


--------------------------------
``this.options`` and ``this.el``
--------------------------------

Now let's start to make our |javascript| module do something useful: show a
`Bootstrap popover <http://getbootstrap.com/2.3.2/javascript.html#popovers>`_
with some extra info about the dataset when the user clicks on the info button.

.. todo:: Insert screenshot.

First, we need our Jinja template to pass some of the dataset's fields to our
|javascript| module as *options*. Change ``package_item.html`` to look like
this:

.. literalinclude:: /../ckanext/example_theme/v17_popover/templates/snippets/package_item.html
   :language: django

This adds some ``data-module-*`` attributes to our ``<button>`` element, e.g.
``data-module-title="{{ package.title }}"`` (``{{ package.title }}`` is a
:ref:`Jinja2 expression <expressions and variables>` that evaluates to the
title of the dataset, CKAN passes the Jinja2 variable ``package`` to our
template).

.. warning::

   Although HTML 5 treats any attribute named ``data-*`` as a data attributes,
   only attributes named ``data-module-*`` will be passed as options to a CKAN
   |javascript| module.

Now let's make use of these options in our |javascript| module. Change
``example_theme_popover.js`` to look like this:

.. literalinclude:: /../ckanext/example_theme/v17_popover/fanstatic/example_theme_popover.js
   :language: javascript

.. note::

   It's best practice to add a docstring to the top of a |javascript| module,
   as in the example above, briefly documenting what the module does and what
   options it takes. See :ref:`javascript module docstrings best practice`.

Any ``data-module-*`` attributes on the HTML element are passed into the
|javascript| module in the object ``this.options``:

.. literalinclude:: /../ckanext/example_theme/v17_popover/fanstatic/example_theme_popover.js
   :language: javascript
   :start-after: // template.
   :end-before: // Format

A |javascript| module can access the HTML element that it was applied to
through the ``this.el`` variable. To add a popover to our info button, we call
Bootstap's ``popover()`` function on the element, passing in an options object
with some of the options that Bootstrap's popovers accept:

.. FIXME: This should be a literal.

::

 // Add a Bootstrap popover to the HTML element (this.el) that this
 // JavaScript module was initialized on.
 this.el.popover({title: this.options.title,
                  content: content,
                  placement: 'left'});


--------------------------
Default values for options
--------------------------

Default values for |javascript| module options can be provided by adding an
``options`` object to the module. If the HTML element doesn't have a
``data-module-*`` attribute for an option, then the default will be used
instead. For example...

.. todo:: Think of an example to do using default values.

.. _ajax:

----------------------------------------------------
Ajax, event handling and CKAN's |javascript| sandbox
----------------------------------------------------

So far, we've used simple |javascript| string formatting to put together the
contents of our popover. If we want the popover to contain much more complex
HTML we really need to render a template for it, using the full power of
:doc:`Jinja2 templates <templates>` and CKAN's
:ref:`template helper functions <template helper functions>`. Let's edit our
plugin to use a Jinja2 template to render the contents of the popups nicely.

.. todo:: Insert a screenshot of the final result.

First, edit ``package_item.html`` to make it pass a few more parameters to the
JavaScript module using ``data-module-*`` attributes:

.. literalinclude:: /../ckanext/example_theme/v18_snippet_api/templates/snippets/package_item.html
   :language: django

We've also added a second ``{% resource %}`` tag to the snippet above, to
include a custom CSS file. We'll see the contents of that CSS file later.

Next, we need to add a new template snippet to our extension that will be used
to render the contents of the popovers. Create this
``example_theme_popover.html`` file::

  ckanext-example_theme/
    ckanext/
      example_theme/
        templates/
          ajax_snippets/
            example_theme_popover.html

and put these contents in it:

.. literalinclude:: /../ckanext/example_theme/v18_snippet_api/templates/ajax_snippets/example_theme_popover.html
   :language: django

This is a Jinja2 template that renders some nice looking contents for a
popover, containing a few bits of information about a dataset. It uses a number
of CKAN's Jinja2 templating features, including marking user-visible strings
for translation and calling template helper functions. See :doc:`templates`
for details about Jinja2 templating in CKAN.

.. note::

   The new template file has to be in a ``templates/ajax_snippets/`` directory
   so that we can use the template from our |javascript| code using
   CKAN's :js:func:`~this.sandbox.client.getTemplate` function. Only templates
   from ``ajax_snippets`` directories are available from the
   :js:func:`~this.sandbox.client.getTemplate` function.

Next, edit ``fanstatic/example_theme_popover.js`` as shown below.
There's a lot going on in this new |javascript| code, including:

* Using `Bootstrap's popover API <http://getbootstrap.com/2.3.2/javascript.html#popovers>`_
  to show and hide popovers, and set their contents.

* Using `jQuery's event handling API <http://api.jquery.com/category/events/>`_
  to get our functions to be called when the user clicks on a button.

* Using a function from CKAN's :doc:`JavaScript sandbox <javascript-sandbox>`.

  The sandbox is a |javascript| object, available to all |javascript| modules
  as ``this.sandbox``, that contains a collection of useful functions and
  variables.

  :js:data:`this.sandbox.client` is a CKAN API client written in |javascript|, that
  should be used whenever a |javascript| module needs to talk to the CKAN API,
  instead of modules doing their own HTTP requests.

  :js:func:`this.sandbox.client.getTemplate` is a function that sends an
  asynchronous (ajax) HTTP request (i.e. send an HTTP request from
  |javascript| and receive the response in |javascript|, without causing
  the browser to reload the whole page) to CKAN asking for a template snippet
  to be rendered.

Hopefully the liberal commenting in the code below makes it clear enough what's
going on:

.. literalinclude:: /../ckanext/example_theme/v18_snippet_api/fanstatic/example_theme_popover.js
   :language: javascript

Finally, we need some custom CSS to make the HTML from our new snippet look
nice. In ``package_item.html`` above we added a ``{% resource %}`` tag to
include a custom CSS file. Now we need to create that file,
``ckanext-example_theme/ckanext/example_theme/fanstatic/example_theme_popover.css``:

.. literalinclude:: /../ckanext/example_theme/v18_snippet_api/fanstatic/example_theme_popover.css
   :language: css

Restart CKAN, and your dataset popovers should be looking much better.


--------------
Error handling
--------------

.. todo::

   Add an example of how to handle error responses when making ajax requests.


.. _pubsub:

------
Pubsub
------

You may have noticed that, with our example code so far, if you click on the
info button of one dataset on the page then click on the info button of another
dataset, both dataset's popovers are shown. The first popover doesn't disappear
when the second appears, and the popovers may overlap. If you click on all the
info buttons on the page, popovers for all of them will be shown at once.

.. todo:: Insert a screenshot of the problem.

To make one popover disappear when another appears, we can use CKAN's
:js:func:`~this.sandbox.client.publish` and
:js:func:`~this.sandbox.client.subscribe` functions. These pair of functions
allow different instances of a JavaScript module (or instances of different
JavaScript modules) on the same page to talk to each other.
The way it works is:

#. Modules can subscribe to events by calling
   :js:func:`this.sandbox.client.subscribe`, passing the 'topic'
   (a string that identifies the type of event to subscribe to) and a callback
   function.

#. Modules can call :js:func:`this.sandbox.client.publish` to
   publish an event for all subscribed modules to receive, passing the topic
   string and one or more further parameters that will be passed on as
   parameters to the receiver functions.

#. When a module calls :js:func:`~this.sandbox.client.publish`, any callback
   functions registered by previous calls to
   :js:func:`~this.sandbox.client.subscribe` with the same topic string will
   be called, and passed the parameters that were passed to publish.

#. If a module no longer wants to receive events for a topic, it calls
   :js:func:`~this.sandbox.client.unsubscribe`.

   All modules that subscribe to events should have a ``teardown()`` function
   that unsubscribes from the event, to prevent memory leaks. CKAN calls the
   ``teardown()`` functions of modules when those modules are removed from the
   page. See :ref:`pubsub unsubscribe best practice`.

.. warning::

   Don't tightly couple your JavaScript modules by overusing pubsub.
   See :ref:`pubsub overuse best practice`.

Remember that because we attach our ``example_theme_popover.js`` module to a
``<button>`` element that is rendered once for each dataset on the page, CKAN
creates one instance of our module for each dataset. The only way these objects
can communicate with each other so that one object can hide its popover when
another object shows its popover, is by using pubsub.

Here's a modified version of our ``example_theme_popover.js`` file that uses
pubsub to make the dataset popovers disappear whenever a new popover appears:

.. literalinclude:: /../ckanext/example_theme/v19_pubsub/fanstatic/example_theme_popover.js
   :language: javascript


--------------
jQuery plugins
--------------

.. todo::

   Can module register their own jQuery plugins?
   If so, provide an example.


.. _javascript i18n:

--------------------
Internationalization
--------------------

.. todo::

   Show how to Internationalize a JavaScript module.


--------------------------
Testing JavaScript modules
--------------------------

.. todo::

   Show how to write tests for the example module.
