=============================
Customizing CKAN's JavaScript
=============================

.. todo:: Link to an introductory JavaScript tutorial.

.. todo:: Introduce the example we're doing here: starring datasets using a
     custom dataset_star action (also need the code to add this action).

.. todo:: Explain that Bootstrap's JavaScript features can be used just by CSS.


--------------------------------
Initializing a JavaScript module
--------------------------------

To get CKAN to call some custom JavaScript code, we need to:

1. Implement a |javascript| module, and register it with CKAN.
   Create the file ``ckanext-example_theme/fanstatic/favorite.js``, with these
   contents:

   .. literalinclude:: /../ckanext/example_theme/v15_initialize_a_javascript_module/fanstatic/favorite.js

   This bit of |javascript| calls the ``ckan.module()`` function to register a
   new JavaScript module with CKAN. ``ckan.module()`` takes two arguments: the
   name of the module being registered (``'favorite'`` in this example) and a
   function that returns the module itself. The function takes two arguments,
   which we'll look at later. The module is just a |javascript| object with a
   single attribute, ``initialize``, whose value is a function that CKAN will
   call to initialize the module. In this example, the initialize function just
   prints out a confirmation message - this |javascript| module doesn't do
   anything interesting yet.

2. Include the |javascript| module in a page, using Fanstatic, and apply it to
   one or more HTML elements on that page. We'll override CKAN's
   ``package_item.html`` template snippet to insert our module whenever a
   package is rendered as part of a list of packages (for example, on the
   dataset search page). Create the file
   ``ckanext-example_theme/templates/snippets/package_item.html`` with these
   contents:

   .. literalinclude:: /../ckanext/example_theme/v15_initialize_a_javascript_module/templates/snippets/package_item.html

   .. todo:: Link to something about HTML data-* attributes.

   If you now restart the development server and open
   http://127.0.0.1:5000/dataset in your web browser, you should see an
   extra "star this dataset" button next to each dataset shown. If you open a
   |javascript| console in your browser, you should see the message that your
   module has printed out.

   .. todo:: Link to something about JavaScript consoles.

   If you have more than one dataset on your page, you'll see the module's
   message printed once for each dataset. The ``package_item.html`` template
   snippet is rendered once for each dataset that's shown in the list, and
   CKAN creates a new instance of your |javascript| module for each dataset.
   If you view the source of your page, however, you'll see that
   ``favorite.js`` is only included with a ``<script>`` tag once. Fanstatic
   is smart enough to deduplicate resources.

   .. note:: |javascript| modules *must* be included as Fanstatic resources,
      you can't add them to a ``public`` directory and include them using your
      own ``<script>`` tags.


--------------------
Responding to events
--------------------

To get our |javascript| module to do something more interesting, we'll use its
initialize function to register some event handler functions which we'll then
use to do some actions in response to events such as mouse clicks. Edit your
``favorite.js`` file to look like this:

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

