=============
Theming guide
=============

The following sections will teach you how to customize the content and
appearance of CKAN pages by developing your own CKAN themes.

.. seealso::

   :doc:`/maintaining/getting-started`
    If you just want to do some simple customizations such as changing the
    title of your CKAN site, or making some small CSS customizations,
    :doc:`/maintaining/getting-started` documents some simple configuration
    settings you can use.

.. note::

  Before you can start developing a CKAN theme, you'll need a working source
  install of CKAN on your system. If you don't have a CKAN source install
  already, follow the instructions in
  :doc:`/maintaining/installing/install-from-source` before continuing.


.. note::

   CKAN theme development is a technical topic, for web developers.
   The tutorials below assume basic knowledge of:

   * `The Python programming language <http://www.python.org/>`_
   * `HTML <https://developer.mozilla.org/en-US/docs/Web/HTML>`_
   * `CSS <https://developer.mozilla.org/en-US/docs/Web/CSS>`_
   * `JavaScript <https://developer.mozilla.org/en-US/docs/Web/JavaScript>`_

   We also recommend familiarizing yourself with:

   * `Jinja2 templates <http://jinja.pocoo.org/docs/templates/>`_
   * `Bootstrap <https://getbootstrap.com/docs/3.4/>`__
   * `jQuery <http://jquery.com/>`_

.. note::

    Starting from CKAN version 2.10 the Bootstrap version used in the default
    CKAN theme is Bootstrap 5. For backwards compatibility, Bootstrap 3 templates
    will be included in CKAN core for a few versions, but they will be eventually
    removed so you are encouraged to update your custom theme to use Bootstrap 5.
    You can select which set of templates to use (Bootstrap 5 or 3) by using the
    :ref:`ckan.base_public_folder` and :ref:`ckan.base_templates_folder`
    configuration options.


.. toctree::
   :maxdepth: 2

   templates
   static-files
   css
   webassets
   javascript
   best-practices
   jinja-tags
   variables-and-functions
   javascript-module-objects-and-methods
   template-helper-functions
   template-snippets
   javascript-sandbox
   javascript-api-client
   jquery-plugins
