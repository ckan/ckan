=============================
Customizing CKAN's JavaScript
=============================

.. warning::

   This is a draft |javascript| tutorial! It's nowhere near finished yet.

.. todo:: Link to an introductory JavaScript tutorial.

.. todo:: Introduce the example we're doing here: starring datasets using a
     custom dataset_star action (also need the code to add this action).

.. todo:: Explain that Bootstrap's JavaScript features can be used just by CSS.


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


--------------------
Responding to events
--------------------

To get our |javascript| module to do something more interesting, we'll use its
initialize function to register some event handler functions which we'll then
use to do some actions in response to events such as mouse clicks. Edit your
``example_theme_popover.js`` file to look like this:

.. Link to some JavaScript tutorial?

   JavaScript modules are the core - every javascripted object should be a
   module. Small, isolated components that can be easily tested. They should
   not use any global objects, all functionality provided to them via a sandbox
   object.

   A module is a JavaScript object with an initialize() and a teardown()
   method.

   Initialize a module with a data-module attribute:
     <select name="format" data-module="autocomplete"></select>

   Or apparently you can also use {% resource %}? Or you have to use resource?

   "favorite" module goes in favorite.js file.

   The idea is that the HTML element should still work fine is JavaScript is
   disabled - e.g. use form submission instead of XHR request.

   You can pass "options objects" with further data-module-* attributes.

   The modules are initialized "on DOM ready", each module's initialize()
   method is called.

   this.sandbox.jQuery - access jQuery methods
   this.sandbox.translte() - i18n
   (or these are the jQuery and _ params of your module function)

   pub/sub for sending messages between modules:
   this.sandbox.publish/subscribe/unsubscribe

   this.sandbox.client should be used to make XHR requests to the CKAN API
   (not jQuery.ajax())

   i18n: this.sandbox.translate(), supports %(name)s, including plurals.
   The options() method of each module should set all strings to be i18n'd?
   Then other code uses this.18n() to retrieve them.

   If not CKAN specific, module functionality should be packaged up in jQuery
   plugins.

   Testing.

