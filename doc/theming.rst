=======
Theming
=======

.. todo::

   Add more to :doc:`getting-started`, is there more that can be done in the
   config file, e.g. site logo?

:doc:`getting-started` documents some simple CKAN configuration settings that
you can use to, for example, change the title of your CKAN site. For those who
want more control over their CKAN site's frontend, this document covers
everything you need to know to develop a custom CKAN theme, including how to
customize CKAN's HTML templates, CSS and |javascript|. The sections below will
walk you through the process of creating a simple, example CKAN theme that
demonstrates all of the main features of CKAN theming.

.. todo::

   Insert link to the completed example theme here.


---------------
Installing CKAN
---------------

Before you can start developing a CKAN theme, you’ll need a working source
install of CKAN on your system. If you don’t have a CKAN source install
already, follow the instructions in :doc:`install-from-source` before
continuing.


-------------------------
Creating a CKAN extension
-------------------------

A CKAN theme must be contained within a CKAN extension, so we'll begin by
creating an extension to hold our theme. As documented in
:doc:`writing-extensions`, extensions can customize and extend CKAN's features
in many powerful ways, but in this example we'll use our extension only to hold
our theme.

.. todo::

   This stuff is duplicated from the writing extensions docs, do a Sphinx
   include here instead.

First, use the ``paster create`` command to create an empty extension:

.. parsed-literal::

   |activate|
   cd |virtualenv|/src
   paster --plugin=ckan create -t ckanext ckanext-example_theme

The command will ask you to answer a few questions. The answers you give will
end up in your extension's ``setup.py`` file (where you can edit them later if
you want).

(See :doc:`writing-extensions` for full documentation on creating CKAN
extensions and plugins.)

Now create the file ``ckanext-example_theme/ckanext/example_theme/plugin.py``
with the following contents:

.. literalinclude:: ../ckanext/example_theme/plugin.py

Now let's add our plugin to the ``entry_points`` in ``setup.py``.  This
identifies the plugin to CKAN once the extension is installed in CKAN's
virtualenv. Edit ``ckanext-example_theme/setup.py`` and add a line to the
``entry_points`` section like this::

    entry_points='''
        [ckan.plugins]
        example_theme=ckanext.example_theme.plugin:ExampleThemePlugin
    ''',

Install the ``example_theme`` extension:

.. parsed-literal::

   |activate|
   cd |virtualenv|/src/ckanext-example_theme
   python setup.py develop

Finally, enable the plugin in your CKAN config file. Edit |development.ini| and
add ``example_theme`` to the ``ckan.plugins`` line, for example::

    ckan.plugins = stats text_preview recline_preview example_theme

You should now be able to start CKAN in the development web server and have it
start up without any problems:

.. parsed-literal::

    $ paster serve |development.ini|
    Starting server in PID 13961.
    serving on 0.0.0.0:5000 view at http://127.0.0.1:5000

If your plugin is in the :ref:`ckan.plugins` setting and CKAN starts without
crashing, then your plugin is installed and CKAN can find it. Of course, your
plugin doesn't *do* anything yet.


--------------------------------------------
Customizing CKAN's HTML and Jinja2 templates
--------------------------------------------

.. todo::

   * Introduce Bootstrap here. A lot of Bootstrap stuff can be done just using
     HTML. It should also get mentioned in other sections (CSS, JavaScript..)
   * HTML (which version?)
   * Jinja2
   * CKAN's custom Jinja2 tags and form macros


---------------------------------------------------------------------
Adding CSS, JavaScript, images and other static files using Fanstatic
---------------------------------------------------------------------

.. todo::

   * Introduce Fanstatic
   * Use the plugin to register a Fanstatic library
   * Use ``{% resource %}`` to load stuff from the library
   * Presumably you can also load stuff from the core library?


----------------------
Customizing CKAN's CSS
----------------------

.. todo::

   * Introduce CSS?
   * Use Fanstatic to add a CSS file
   * Use Bootstrap's CSS files and CKAN core's
   * See the CKAN style guide


-----------------------------
Customizing CKAN's JavaScript
-----------------------------

.. todo::

   * How to load JavaScript modules
   * jQuery
   * Bootstrap's JavaScript stuff
   * Other stuff in javascript-module-tutorial.rst





----

Create Custom Extension
-----------------------

This method is best for you want to customize the HTML templates of you CKAN
instance. It's also more extensible and means you can make sure you keep your
custom theme as seperate from CKAN core as possible.

Here follows the main topics you'll need in order to understand how to write
a custom extension in order to customize your CKAN instance.


Customizing the HTML
~~~~~~~~~~~~~~~~~~~~

The main templates within CKAN use the templating language `Jinja2`_. Jinja2
has template inheritance which means that you don't have to re-write a whole
template in order to change small elements within templates.

For more information on how to exactly change the HTML of your CKAN instance: 
please read the `Templating > Templating within extensions`_ documentation.


Including custom Stylesheets, JavaScript and images
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within CKAN we use a resource manager to handle the static resources that are
required by any given template. In order to include a stylesheet or a
JavaScript document you should tell the resource manager of its existence and
then include it within your template.

For more information on how resources work within CKAN and how to add custom
resources to your extension: please read the 
`Resources > Resources within extensions`_ documentation.

.. Note::
    The main CKAN theme is a heavily customized version of `Bootstrap`_.
    However the core of Bootstrap is no different in CKAN and therefore people
    familiar with Bootstrap should feel right at home writing custom HTML and
    CSS for CKAN.


Customizing the JavaScript
~~~~~~~~~~~~~~~~~~~~~~~~~~

Within CKAN core we have a concept of JavaScript modules which allow you to
simply attach JavaScript to DOM elements via HTML5 data attributes.

For more information on what a JavaScript module is and how to build one:
please read the `Building a JavaScript Module`_ documentation.


Customizing the CSS
~~~~~~~~~~~~~~~~~~~

To customize your CSS all you really need to know is how to add a stylesheet as
a resource. Beyond that it's purely writing your own CSS and making sure it's
included on the correct pages.

For more information on how CSS works in CKAN core: please read the
`Front End Documentation > Stylesheets`_ documentation.

.. Note::
    In CKAN core we use `LESS`_ to pre-process our main CSS document. We do
    this to make the core CSS more maintainable (as well as to offer different
    basic colour styles on our default theme). It's not necessary that you do
    the same, but we'd recommend using something like it if you plan on
    customizing your CKAN instance heavily.


.. _Bootstrap: http://getbootstrap.com/
.. _Jinja2: http://Jinja2.pocoo.org/
.. _markdown: http://daringfireball.net/projects/markdown/
.. _LESS: http://lesscss.org/
.. _Templating > Templating within extensions: ./templating.html#templating-within-extensions
.. _Resources > Resources within extensions: ./resources.html#resources-within-extensions
.. _Building a JavaScript Module: ./javascript-module-tutorial.html
.. _Front End Documentation > Stylesheets: ./frontend-development.html#stylesheets
.. _CKAN Configuration Options > Front-End Settings: ./configuration.html#front-end-settings
.. _CKAN Configuration Options > Theming Settings: ./configuration.html#theming-settings

