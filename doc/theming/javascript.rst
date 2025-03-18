.. _javascript_modules:

=============================
Customizing CKAN's JavaScript
=============================

JavaScript code in CKAN is broken down into *modules*: small, independent units
of JavaScript code. CKAN themes can add JavaScript features by providing their
own modules. This tutorial will explain the main concepts involved in CKAN
JavaScript modules and walk you through the process of adding custom modules
to themes.

.. seealso::

   This tutorial assumes a basic understanding of CKAN plugins and templating,
   see:

   * :doc:`/extensions/index`

   * :doc:`/theming/templates`


.. seealso::

   This tutorial assumes a basic understanding of |javascript| and |jquery|,
   see:

   * `JavaScript on the Mozilla Developer Network <https://developer.mozilla.org/en-US/docs/Web/JavaScript>`_

   * `jQuery.com <http://jquery.com/>`_, including the
     `jQuery Learning Center <http://learn.jquery.com/>`_

.. seealso::

   :doc:`/contributing/string-i18n`
     How to mark strings for translation in your JavaScript code.


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
JavaScript). The user experience may not be quite as nice without |JavaScript|,
but the functionality should still be there. This is a programming technique
known as *graceful degradation*, and is a basic tenet of web accessibility.

In the sections below, we'll walk you through the steps to add a new JavaScript
feature to CKAN - dataset info popovers. We'll add an info button to each
dataset on the datasets page which, when clicked, opens a popover containing
some extra information and user actions related to the dataset:

.. image:: /images/example_theme_javascript_popover.png
   :alt: A dataset info popover


--------------------------------
Initializing a JavaScript module
--------------------------------

To get CKAN to call some custom JavaScript code, we need to:

1. Implement a |javascript| module, and register it with CKAN.
   Create the file ``ckanext-example_theme/ckanext/example_theme_docs/assets/example_theme_popover.js``, with these
   contents:

   .. literalinclude:: /../ckanext/example_theme_docs/v16_initialize_a_javascript_module/assets/example_theme_popover.js
      :language: javascript

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

      |javascript| module names should begin with the name of the extension,
      to avoid conflicting with other modules. See :ref:`avoid name clashes`.

   .. note::

      Each |javascript| module's ``initialize()`` function is called on
      `DOM ready <http://api.jquery.com/ready/>`_.

2. Include the |javascript| module in a page, using Assets, and apply it to
   one or more HTML elements on that page. We'll override CKAN's
   ``package_item.html`` template snippet to insert our module whenever a
   package is rendered as part of a list of packages (for example, on the
   dataset search page). Create the file
   ``ckanext-example_theme/ckanext/example_theme_docs/templates/snippets/package_item.html`` with these
   contents:

   .. literalinclude:: /../ckanext/example_theme_docs/v16_initialize_a_javascript_module/templates/snippets/package_item.html
      :language: django

   .. seealso::

      `Using data-* attributes <https://developer.mozilla.org/en-US/docs/Web/Guide/HTML/Using_data_attributes>`_
      on the Mozilla Developer Network.

   If you now restart the development server and open
   http://127.0.0.1:5000/dataset in your web browser, you should see an
   extra info button next to each dataset shown. If you open a
   |javascript| console in your browser, you should see the message that your
   module has printed out.

   .. seealso::

      Most web browsers come with built-in developer tools including a
      |javascript| console that lets you see text printed by |javascript| code
      to ``console.log()``, a |javascript| debugger, and more. For example:

      * `Firefox Developer Tools <https://developer.mozilla.org/en-US/docs/Tools>`_
      * `Firebug <https://www.getfirebug.com/>`_
      * `Chrome DevTools <https://developers.google.com/chrome-developer-tools/>`_

   If you have more than one dataset on your page, you'll see the module's
   message printed once for each dataset. The ``package_item.html`` template
   snippet is rendered once for each dataset that's shown in the list, so your
   ``<button>`` element with the ``data-module="example_theme_popover"``
   attribute is rendered once for each dataset, and CKAN creates a new instance
   of your |javascript| module for each of these ``<button>`` elements.  If you
   view the source of your page, however, you'll see that
   ``example_theme_popover.js`` is only included with a ``<script>`` tag once.
   Assets is smart enough to deduplicate resources.

   .. note:: |javascript| modules *must* be included as Assets resources,
      you can't add them to a ``public`` directory and include them using your
      own ``<script>`` tags.


.. _options and el:

--------------------------------
``this.options`` and ``this.el``
--------------------------------

Now let's start to make our |javascript| module do something useful: show a
`Bootstrap popover <http://getbootstrap.com/2.3.2/javascript.html#popovers>`_
with some extra info about the dataset when the user clicks on the info button.

First, we need our Jinja template to pass some of the dataset's fields to our
|javascript| module as *options*. Change ``package_item.html`` to look like
this:

.. literalinclude:: /../ckanext/example_theme_docs/v17_popover/templates/snippets/package_item.html
   :language: django

This adds some ``data-module-*`` attributes to our ``<button>`` element, e.g.
``data-module-title="{{ package.title }}"`` (``{{ package.title }}`` is a
:ref:`Jinja2 expression <expressions and variables>` that evaluates to the
title of the dataset, CKAN passes the Jinja2 variable ``package`` to our
template).

.. warning::

   Although HTML 5 treats any attribute named ``data-*`` as a data attribute,
   only attributes named ``data-module-*`` will be passed as options to a CKAN
   |javascript| module. So we have to named our parameters
   ``data-module-title`` etc., not just ``data-title``.

Now let's make use of these options in our |javascript| module. Change
``example_theme_popover.js`` to look like this:

.. literalinclude:: /../ckanext/example_theme_docs/v17_popover/assets/example_theme_popover.js
   :language: javascript

.. note::

   It's best practice to add a docstring to the top of a |javascript| module,
   as in the example above, briefly documenting what the module does and what
   options it takes. See :ref:`javascript module docstrings best practice`.

Any ``data-module-*`` attributes on the HTML element are passed into the
|javascript| module in the object ``this.options``:

.. literalinclude:: /../ckanext/example_theme_docs/v17_popover/assets/example_theme_popover.js
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

.. seealso::

   For other objects and functions available to |javascript| modules, see
   :doc:`javascript-module-objects-and-methods`.


--------------------------
Default values for options
--------------------------

Default values for |javascript| module options can be provided by adding an
``options`` object to the module. If the HTML element doesn't have a
``data-module-*`` attribute for an option, then the default will be used
instead. For example...

.. todo:: Think of an example to do using default values.


.. _pubsub:

------
Pubsub
------

You may have noticed that, with our example code so far, if you click on the
info button of one dataset on the page then click on the info button of another
dataset, both dataset's popovers are shown. The first popover doesn't disappear
when the second appears, and the popovers may overlap. If you click on all the
info buttons on the page, popovers for all of them will be shown at once:

.. image:: /images/example_theme_overlapping_popovers.png
   :alt: Dataset info popovers overlapping with eachother

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


.. _javascript i18n:

--------------------
Internationalization
--------------------

See :ref:`javascript_i18n`.

--------------------------
Testing JavaScript modules
--------------------------

.. todo::

   Show how to write tests for the example module.
