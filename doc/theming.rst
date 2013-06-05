=======
Theming
=======

If you want more control over your CKAN site's layout and appearance than the
options described in :doc:`getting-started` give, you can further customize
CKAN's appearance by developing a theme. CKAN's templates, HTML and CSS are all
completely customizable by themes. This document will walk you through the
process of developing a CKAN theme.


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

