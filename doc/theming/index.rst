=======
Theming
=======

.. versionchanged:: 2.0
   The CKAN frontend was completely rewritten for CKAN 2.0, so most of the
   tutorials below don't apply to earlier versions of CKAN.

The CKAN web interface's HTML, CSS and JavaScript are fully customizable by
creating a CKAN theme. The tutorials below will show you how to develop your
own custom CKAN theme.

.. seealso::

   :doc:`/getting-started`
    If you just want to do some simple customizations such as changing the
    title of your CKAN site, or making some small CSS customizations,
    :doc:`/getting-started` documents some simple configuration settings you
    can use.

.. note::

  Before you can start developing a CKAN theme, you’ll need a working source
  install of CKAN on your system. If you don't have a CKAN source install
  already, follow the instructions in :doc:`/install-from-source` before
  continuing.


.. note::

   CKAN theme development is a technical topic, for web developers.
   The tutorials below assume basic knowledge of:

   * `The Python programming language <http://www.python.org/>`_
   * `HTML <https://developer.mozilla.org/en-US/docs/Web/HTML>`_
   * `CSS <https://developer.mozilla.org/en-US/docs/Web/CSS>`_
   * `JavaScript <https://developer.mozilla.org/en-US/docs/Web/JavaScript>`_

   We also recommend familiarizing yourself with:

   * `Jinja2 templates <http://jinja.pocoo.org/docs/templates/>`_
   * `Bootstrap <http://getbootstrap.com/2.3.2/>`_
   * `jQuery <http://jquery.com/>`_

.. toctree::
   :maxdepth: 2

   templates
   static-files
   css
   fanstatic
   javascript
   best-practices
   jinja-tags
   variables-and-functions
   template-helper-functions
   template-snippets
