==================================
Theming and Customizing Appearance
==================================

After installing CKAN, the next step is probably to re-theme the site. There
are a few different ways you can do this. Ranging from simply changing the logo
and adding some simple CSS to writing a extension that will fully customize
the look and feel of your instance.

Here are the two main ways you can customize the appearance of CKAN:

1. `Edit CKAN config options`_
2. `Create Custom Extension`_


Edit CKAN config options
------------------------

This method is best if you simply want to change the logo, title and perhaps
add a little custom CSS. You can edit your CKAN config options at
http://localhost:5000/ckan-admin/config (assuming you are logged within a 
sysadmin account).

Here are the basic config options you can change:

- **Site Title:** This is the title of this CKAN instance. It appears in the page title and various other places throughout your CKAN instance.

- **Style:** Choose from a list of simple variations of the main colour scheme to get a very quick custom theme working.

- **Site Tag Logo:** This is the logo that appears in the header of all the CKAN instance templates. If you want to add a custom logo we recommened you do it here.

- **About:** This text will appear on this CKAN instances about page. We support markdown within this field.

- **Intro Text:** This text will appear on this CKAN instances home page as a welcome to visitors. Again markdown is supported here.

- **Custom CSS:** This is a block of CSS that appears in ``<head>`` tag of every page. If you wish to customize the templates more fully we recommend using the extension method of customizing your CKAN instance.

.. Note::
    You can also change your ``site_title`` within your development.ini.
    However changing the 'Site Title' within the ckan admin interface will
    override this setting.


Create Custom Extension
-----------------------

This method is best for if you want to customize the HTML templates of you CKAN
instance. It's also more extensible and means you can make sure you keep your
custom theme as seperate from CKAN core as possible.

Here follows the main topics you'll need in order to understand how to write
a custom extension in order to customize your CKAN instance.


Customizing the HTML
~~~~~~~~~~~~~~~~~~~~

The main templates within CKAN use the templating language `Jinja`_. Jinja has
template inheritance which means that you don't have to re-write a whole
template in order to change small elements within templates.

For more information on how to exactly change the HTML of your CKAN instance: 
please read the `Templating > CKAN Extensions`_ documentation.


Including custom Stylesheets, JavaScript and images
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within CKAN we use a resource manager called `Fanstatic`_ to handle the static
resources that are required by any given template. In order to include a
stylesheet or a JavaScript document you should tell Fanstatic of its existence
and then include it within your template.

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

To customize your CSS all you really need to know is how to add one as a
fanstatic resource. Beyond that it's purely writing your own CSS and making
sure it's included on the correct pages.

For more information on how CSS works in CKAN core: please read the
`Front End Documentation > Stylesheets`_ documentation.

.. Note::
    In CKAN core we use `LESS`_ to pre-process our main CSS document. We do this
    to make the core CSS more maintainable (as well as to offer different
    basic colour styles on our default theme). It's not necessary that you do
    the same, but we'd recommend using something like it if you plan on
    customizing your CKAN instance heavily.


.. _Bootstrap: http://getbootstrap.com/
.. _Jinja: http://jinja.pocoo.org/
.. _Fanstatic: http://fanstatic.org/
.. _LESS: http://lesscss.org/
.. _Templating > CKAN Extensions: ./templating.html#ckan-extensions
.. _Resources > Resources within extensions: ./resources.html#resources-within-extensions
.. _Building a JavaScript Module: ./javascript-module-tutorial.html
.. _Front End Documentation > Stylesheets: ./frontend-development.html#stylesheets
