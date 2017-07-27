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
   Create the file ``ckanext-example_theme/ckanext/example_theme_docs/fanstatic/example_theme_popover.js``, with these
   contents:

   .. literalinclude:: /../ckanext/example_theme_docs/v16_initialize_a_javascript_module/fanstatic/example_theme_popover.js
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

2. Include the |javascript| module in a page, using Fanstatic, and apply it to
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
   Fanstatic is smart enough to deduplicate resources.

   .. note:: |javascript| modules *must* be included as Fanstatic resources,
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

.. literalinclude:: /../ckanext/example_theme_docs/v17_popover/fanstatic/example_theme_popover.js
   :language: javascript

.. note::

   It's best practice to add a docstring to the top of a |javascript| module,
   as in the example above, briefly documenting what the module does and what
   options it takes. See :ref:`javascript module docstrings best practice`.

Any ``data-module-*`` attributes on the HTML element are passed into the
|javascript| module in the object ``this.options``:

.. literalinclude:: /../ckanext/example_theme_docs/v17_popover/fanstatic/example_theme_popover.js
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

First, edit ``package_item.html`` to make it pass a few more parameters to the
JavaScript module using ``data-module-*`` attributes:

.. literalinclude:: /../ckanext/example_theme_docs/v18_snippet_api/templates/snippets/package_item.html
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

.. literalinclude:: /../ckanext/example_theme_docs/v18_snippet_api/templates/ajax_snippets/example_theme_popover.html
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

.. literalinclude:: /../ckanext/example_theme_docs/v18_snippet_api/fanstatic/example_theme_popover.js
   :language: javascript

Finally, we need some custom CSS to make the HTML from our new snippet look
nice. In ``package_item.html`` above we added a ``{% resource %}`` tag to
include a custom CSS file. Now we need to create that file,
``ckanext-example_theme/ckanext/example_theme/fanstatic/example_theme_popover.css``:

.. literalinclude:: /../ckanext/example_theme_docs/v18_snippet_api/fanstatic/example_theme_popover.css
   :language: css

Restart CKAN, and your dataset popovers should be looking much better.


--------------
Error handling
--------------

What if our JavaScript makes an Ajax request to CKAN, such as our
:js:func:`~this.sandbox.client.getTemplate` call above, and gets an error in
response? We can simulate this by changing the name of the requested template
file to one that doesn't exist:

.. literalinclude:: /../ckanext/example_theme_docs/v19_01_error/fanstatic/example_theme_popover.js
   :language: javascript
   :start-after: if (!this._snippetReceived) {
   :end-before: this._snippetReceived = true;

If you reload the datasets page after making this change, you'll see that when
you click on a popover its contents remain *Loading...*. If you have a
development console open in your browser, you'll see the error response from
CKAN each time you click to open a popover.

Our JavaScript module's ``_onReceiveSnippet()`` function is only called if the
request gets a successful response from CKAN.
:js:func:`~this.sandbox.client.getTemplate` also accepts a second callback
function parameter that will be called when CKAN sends an error response.
Add this parameter to the :js:func:`~this.sandbox.client.getTemplate` call:

.. literalinclude:: /../ckanext/example_theme_docs/v19_02_error_handling/fanstatic/example_theme_popover.js
   :language: javascript
   :start-after: if (!this._snippetReceived) {
   :end-before: _onReceiveSnippet: function(html) {

Now add the new error function to the JavaScript module:

.. literalinclude:: /../ckanext/example_theme_docs/v19_02_error_handling/fanstatic/example_theme_popover.js
   :language: javascript
   :start-after: // This function is called when CKAN responds with an error.
   :end-before: // End of _onReceiveSnippetError

After making these changes, you should see that if CKAN responds with an
error, the contents of the popover are replaced with the error message from
CKAN.


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

Remember that because we attach our ``example_theme_popover.js`` module to a
``<button>`` element that is rendered once for each dataset on the page, CKAN
creates one instance of our module for each dataset. The only way these objects
can communicate with each other so that one object can hide its popover when
another object shows its popover, is by using pubsub.

Here's a modified version of our ``example_theme_popover.js`` file that uses
pubsub to make the dataset popovers disappear whenever a new popover appears:

.. literalinclude:: /../ckanext/example_theme_docs/v20_pubsub/fanstatic/example_theme_popover.js
   :language: javascript


--------------
jQuery plugins
--------------

CKAN provides a number of custom jQuery plugins for JavaScript modules to use
by default, see :doc:`jquery-plugins`.
Extensions can also add their own jQuery plugins, and the plugins will then be
available to all JavaScript code via the :js:data:`this.$` object.

.. seealso::

   `How to Create a Basic Plugin <http://learn.jquery.com/plugins/basic-plugin-creation/>`_
     jQuery's own documentation on writing jQuery plugins. Read this for all
     the details on writing jQuery plugins, here we'll only provide a simple
     example and show you how to integrate it with CKAN.

It's a good idea to implement any JavaScript functionality not directly related
to CKAN as a jQuery plugin. That way your CKAN JavaScript modules will be
smaller as they'll contain only the CKAN-specific code, and your jQuery plugins
will also be reusable on non-CKAN sites. CKAN core uses jQuery plugins to
implement features including date formatting, warning users about unsaved
changes when leaving a page containing a form without submitting the form,
restricting the set of characters that can be typed into an input field, etc.

Let's add a jQuery plugin to our CKAN extension that makes our info buttons
turn green when clicked.

.. todo:: Replace this with a more realistic example.

First we need to write the jQuery plugin itself. Create the file
``ckanext-example_theme/ckanext/example_theme/fanstatic/jquery.greenify.js``
with the following contents:

.. literalinclude:: /../ckanext/example_theme_docs/v21_custom_jquery_plugin/fanstatic/jquery.greenify.js
   :language: javascript

If this JavaScript code looks a little confusing at first, it's probably
because it's using the
`Immediately-Invoked Function Expression (IIFE) <https://en.wikipedia.org/wiki/Immediately-invoked_function_expression>`_
pattern. This is a common JavaScript code pattern in which an anonymous
function is created and then immediately called once, in a single expression.
In the example above, we create an unnamed function that takes a single
parameter, ``jQuery``, and then we call the function passing ``this.jQuery``
to its ``jQuery`` parameter. The code inside the body of the function is the
important part. Writing jQuery plugins in this way ensures that
any variables defined inside the plugin are private to the plugin, and don't
pollute the global namespace.

In the body of our jQuery plugin, we add a new function called ``greenify()``
to the ``jQuery`` object:

.. literalinclude:: /../ckanext/example_theme_docs/v21_custom_jquery_plugin/fanstatic/jquery.greenify.js
   :language: javascript
   :start-after: (function (jQuery) {
   :end-before: })(this.jQuery);

``jquery.fn`` is the jQuery prototype object, the object that normal jQuery
objects get all their methods from. By adding a method to this object, we
enable any code that has a jQuery object to call our method on any HTML element
or set of elements. For example, to turn all ``<a>`` elements on the page green
you could do: ``jQuery('a').greenify()``.

The code inside the ``greenify()`` function just calls jQuery's standard
`css() <http://api.jquery.com/css/>`_ method to set the CSS ``color``
attribute of the element to ``green``. This is just standard jQuery code,
except that within a custom jQuery function you use ``this`` to refer to the
jQuery object, instead of using ``$`` or ``jquery`` (as you would normally do
when calling jQuery methods from code external to jQuery).

Our method then returns ``this`` to allow jQuery method chaining to be used
with our method. For example, a user can set an element's CSS ``color``
attribute to ``green`` and add the CSS class ``greenified`` to the element in
a single expression by chaining our jQuery method with another method:
``$('a').greenify().addClass('greenified');``

Before we can use our ``greenify()`` method in CKAN, we need to import the
``jquery.greenify.js`` file into the CKAN page. To do this, add a
``{% resource %}`` tag to a template file, just as you would do to include any
other JavaScript or CSS file in CKAN. Edit the ``package_item.html`` file:

.. literalinclude:: /../ckanext/example_theme_docs/v21_custom_jquery_plugin/templates/snippets/package_item.html
   :language: django

Now we can call the ``greenify()`` method from our ``example_theme_popover``
JavaScript module. For example, we could add a line to the ``_onClick()``
method in ``example_theme_popover.js`` so that when a dataset info button is
clicked it turns green:

.. literalinclude:: /../ckanext/example_theme_docs/v21_custom_jquery_plugin/fanstatic/example_theme_popover.js
   :language: javascript
   :start-after: // Start of _onClick method.
   :end-before: // End of _onClick method.

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
