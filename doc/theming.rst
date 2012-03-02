==================================
Theming and Customizing Appearance
==================================

After installing CKAN, the next step is probably to re-theme the site with your own logo, site name, and CSS. 

Site Name and Description
=========================

You can change the name and logo of the site by setting options in the CKAN config file. 

This is the file called ``std.ini`` that you first encountered in :ref:`create-admin-user`. It is usually located at ``/etc/ckan/std/std.ini``.

Open this file, and change the following options::

 ckan.site_title = My CKAN Site
 ckan.site_description = The easy way to get, use and share data

After you've edited these options, restart Apache::

 sudo /etc/init.d/apache2 restart

Refresh your home page (clearing the cache if necessary) and you should see your new title and description. 


Adding CSS, Javascript and other HTML using Config Options
==========================================================

CKAN provides two config options that allow you to add material directly into templates::

  ckan.template_head_end = ...
  ckan.template_footer_end = ...

The first of these allows you to specify content that will be inserted just before ``</head>`` tag while the second allows you to insert content just before the ``</body>``. You can use html in both of these as well as provide multiline values by indenting lines.

Adding CSS
----------

For example, by referencing an external CSS stylesheet::

  ckan.template_head_end = <link rel="stylesheet" href="http://some-other-site.org/custom.css" type="text/css"> 

.. note::

  This requires you have a css file uploaded elsewhere. You may want your css to be part of your CKAN site. CKAN provides an easy way to do this -- see ``extra_public_paths`` below.

Alternatively you can provide CSS directly in a style tag (note how we indent lines to provide a multiline value to a config option)::

  ckan.template_head_end = <style type="text/css"> 
      body {
        font-size: xlarge;
      }
    </style>

Adding Javascript
-----------------

You could also use this config option to add script tags (or any other material to the ``<head>`` of all site pages).

However, for javascript it is probably better to use the ``ckan.template_footer_end`` option as it adds material just before the closing ``</body>`` tag -- in CKAN v1.5 scripts are included at the foot of the page rather than in the <head> section (thus if your scripts requires jquery it needs to come after jqurey is included at the bottom of the page and hence you should use the footer end option).


More Advanced Customization
===========================

If you want to make broader changes to the look and feel of your CKAN site, we offer ways to add custom CSS and over-ride the default CKAN templates. 

Adding (and Overriding) Files and Templates
-------------------------------------------

You can add (and override) files (e.g. CSS, scripts and images) as well as templates to your site using the ``extra_template_paths`` and ``extra_public_paths`` options in the CKAN config file::

 extra_template_paths = %(here)s/my-templates
 extra_public_paths = %(here)s/my-public

All contents of the public directory is mounted directly into the URL space of the site (taking precedence over existing files of the same name). 

Furthermore, you can supply multiple public directories, which will be searched in order. 

For example, if you set the following option in the CKAN config file::

 extra_public_paths = /path/to/mypublicdir 

And then add a file called ``myhtmlfile.html`` in ``/path/to/mypublicdir``, the file would appear on http://yourckan.org/ at ``http://yourckan.org/myhtmlfile.html``. 

If you create a file with the same path as one in the main CKAN public directory, your file will override the default CKAN file. For example, if you add ``mypublicdir/css/ckan.css``, then ``http://yourckan.org/css/ckan.css`` will be your file. 

Adding a New Logo
^^^^^^^^^^^^^^^^^

One example is introducing your own logo, which you can do with a new file and a CKAN config option. 

Add a logo file at ``mypublicdir/images/mylogo.png``, then set options in the CKAN config file (``/etc/ckan/std/std.ini``) as follows::

 extra_public_paths = /path/to/mypublicdir
 ckan.site_logo = /images/mylogo.png


Adding a New Stylesheet
^^^^^^^^^^^^^^^^^^^^^^^

Lots of visual changes can be made simply by changing the stylesheet. We've already 

The easiest way to override the default CKAN style is to create one or more custom CSS files and load them in the ``layout.html`` template.

Use the 'public' directory as described in the previous section, then add a new file at ``mypublicdir/css/mycss.css``.

Your next step is to have that css file including by the templates.

Next, copy the ``layout.html`` template and add a reference to the new CSS file. Here is an example of the edited ``layout.html`` template::

  <html xmlns="http://www.w3.org/1999/xhtml"
    xmlns:i18n="http://genshi.edgewall.org/i18n"
    xmlns:py="http://genshi.edgewall.org/" 
    xmlns:xi="http://www.w3.org/2001/XInclude"
    py:strip="">
    <head py:match="head">
      ${select('*')}
      <link rel="stylesheet" href="${h.url_for('/css/mycss.css')}" />
    </head>
    <xi:include href="layout_base.html" />
  </html>

Retheming the Site with Templates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Template files are used as source templates for rendered pages on the site. These templates are just an HTML page but with variables, such as the page title set by each page: ``${page_title}``.

To over-ride a template, set the ``extra_template_paths`` directory as described above, then copy and rewrite the template file you wish to over-ride. 

Commonly modified templates are:

 * ``layout.html`` - empty by default
 * ``home/index.html`` - the home page of the site
 * ``home/about.html`` - the about page

If you are re-theming the site, we recommend you over-ride ``layout.html``, which is empty but inherits from ``layout_base.html``. This will mean you can upgrade the site more easily in the future. 

.. note::

  For more information on the syntax of the CKAN templates, refer to the `Genshi documentation <http://genshi.edgewall.org/wiki/Documentation>`_.
