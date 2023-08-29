=====================================================
Objects and methods available to |javascript| modules
=====================================================

CKAN makes a few helpful objects and methods available for every JavaScript
module to use, including:

* ``this.el``, the HTML element that this instance of the object was
  initialized for. A jQuery element. See :ref:`options and el`.

* ``this.options``, an object containing any options that were passed to the
  module via ``data-module-*`` attributes in the template.
  See :ref:`options and el`.

* :js:data:`this.$()`, a jQuery find function that is scoped to the HTML
  element that the JavaScript module was applied to. For example,
  ``this.$('a')`` will return all of the ``<a>`` elements inside the module's
  HTML element, *not* all of the ``<a>`` elements on the entire page.

  This is a shortcut for ``this.el.find()``.

  jQuery provides many useful features in an easy-to-use API, including
  document traversal and manipulation, event handling, and animation. See
  `jQuery's own docs <http://jquery.com/>`_ for details.

.. _this_sandbox:

* :js:data:`this.sandbox`, an object containing useful functions for all
  modules to use, including:

  * :js:data:`this.sandbox.client`, an API client for calling the API

  * :js:data:`this.sandbox.jQuery`, a jQuery find function that is not bound to
    the module's HTML element. ``this.sandbox.jQuery('a')`` will return all the
    ``<a>`` elements on the entire page.
    Using :js:data:`this.sandbox.jQuery` is discouraged, try to stick to
    :js:data:`this.$` because it keeps |javascript| modules more independent.

  See :doc:`javascript-sandbox`.

* A collection of :doc:`jQuery plugins <jquery-plugins>`.

* :ref:`Pubsub functions <pubsub>` that modules can use to communicate with
  each other, if they really need to.

* Bootstrap's JavaScript features, see the
  `Bootstrap docs <https://getbootstrap.com/docs/3.4/javascript/>`__
  for details.

* The standard |javascript| ``window`` object. Using ``window`` in CKAN
  |javascript| modules is discouraged, because it goes against the idea of a
  module being independent of global context. However, there are some
  circumstances where a module may need to use ``window`` (for example if a
  vendor plugin that the module uses needs it).

* ``this._`` and ``this.ngettext`` for string internationalization. See
  :ref:`javascript i18n`.

* ``this.remove()``, a method that tears down the module and removes it from
  the page (this usually called by CKAN, not by the module itself).
