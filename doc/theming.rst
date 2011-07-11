=============
Customization
=============

After installing CKAN, the next step is probably to re-theme the site with your own logo, site name, and CSS. 

Logo and Site Name
==================

The name and logo of the site can be easily changed throughout the site by changing the CKAN config file::

 ckan.site_title = My Site Title
 ckan.site_logo = http://mysite.org/mylogo.png
 ckan.site_description = The easy way to get, use and share data


Custom CSS with Themes
======================

You can make changes to CKAN's theme by editing files in the CKAN code package.

However, it's best not to edit the files that are checked into the CKAN repository, because it makes upgrading these CKAN files more difficult. It is also handy to keep your changes in a separate place.

Instead, configure CKAN to look for custom files that override the CKAN core files. As well as templates, you can add HTML, stylesheets, scripts, images etc.

These are set up using the ``extra_template_paths`` and ``extra_public_paths`` options in the CKAN config file::

 ## extra places to look for templates and public files (comma separated lists)
 ## any templates/files found will override correspondingly named ones in
 ## ckan/templates/ and ckan/public respectively
 ## (e.g. to override main layout template layout.html or add in css/extra.css)
 extra_template_paths = %(here)s/my-templates
 extra_public_paths = %(here)s/my-public
 [edit] Public Directory

All contents of the public directory is mounted directly into the url space of the site (taking precedence over any other similarly named file). Furthermore you can have multiple public directories and they are searched in order with first match used with the last searched being the public directory supplied in the ckan package.

To illustrate:
# ckan ini file
extra_public_paths = /path/to/mypublicdir 

# mypublicdir
mypublicdir/mycss.css
mypublicdir/images/mylogo.png
mypublicdir/myhtmlfile.html 

# will appear on site http://yourckan.org/ at:
http://yourckan.org/mycss.css

http://yourckan.org/myhtmlfile.html 

# if you create a file with the same path
# as one in the main CKAN public dir
# e.g.
mypublicdir/css/ckan.css
# this will override the main CKAN one
http://yourckan.org/css/ckan.css -- will be your ckan.css ...
[edit] Editing CSS

Lots of visual changes can be done simply by changing the stylesheet. The easiest way to override the default CKAN style is to create one or more custom CSS files and loading them in the layout.html template (see next section)::

 <html xmlns="http://www.w3.org/1999/xhtml"
   xmlns:i18n="http://genshi.edgewall.org/i18n"
   xmlns:py="http://genshi.edgewall.org/"
   xmlns:xi="http://www.w3.org/2001/XInclude"
   py:strip="">
   <py:def function="optional_head">
       <link rel="stylesheet" href="${g.site_url}/css/mycss.css" />
   </py:def>
   <xi:include href="layout_base.html" />
 </html>

For more extensive changes and introduction of images etc use the 'public' directory as described in the previous section. For example, to introduce your own logo:

mypublicdir/images/mylogo.png

# ckan ini file (config)
extra_public_paths = /path/to/mypublicdir
ckan.site_logo = /images/mylogo.png
[edit] Editing templates

Template files are simple: these files are what we use as source templates for rendered pages on the site. These templates are just an html page but with some variables, such as this one set by each page: ${page_title}

Templates of particular interest are:

 * layout_base.html - base layout template for whole site 
 * layout.html - by default this is empty (you can use this template to override some things in layout_base.html without having to change layout_base.html)
 * home/index.html - the home page of the site
 * home/about.html - the about page

Re-theming the entire site
--------------------------

To re-theme you want to edit layout.html or layout_base.html. (NB: you may be able to do most re-theming just using css -- see above).

It is better to create your own templates directory and point to it using the extra_template_paths config option than edit the layout_base.html in the CKAN code package. Any templates found in this directory will then be used instead of the original 'default' ckan template.

Making simple layout template changes using layout.html rather than layout_base.html

If you only want to change a small part of the layout, it would be instead better to create a replacement for ckan/templates/layout.html. layout.html 'inherits' from layout_base.py and you can selectively override layout_base.html in layout.html. The advantage of this is that layout_base.html can be upgraded and your changes will still work.

For example here we add some Typekit initialisation to the <head> and replace the h1 tag with a new title image for the site:

<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://genshi.edgewall.org/" 
  xmlns:xi="http://www.w3.org/2001/XInclude"
  xmlns:doap="http://usefulinc.com/ns/doap"
  xmlns:foaf="http://xmlns.com/foaf/0.1/"
  py:strip=""
  >
  <py:match path="head">
    <head>
      ${select('*')}
      <!-- Typekit embed code -->
      <script type="text/javascript" src="http://use.typekit.com/wty5dhe.js"></script>
        <script type="text/javascript">try{Typekit.load();}catch(e){}</script>
      <!-- /Typekit -->
    </head>
  </py:match>
  <py:match path="h1">
    <h1 id="page-title">
      <a href="${h.url_for(controller='site')}" title="${c.site_title} Home">
        <img src="/images/Brazil_OD.png" alt="Brazil Open Data" class="logo" />
      </a>
    </h1>
  </py:match>
  <xi:include href="layout_base.html" />
</html>

Changing Individual Pages
-------------------------

You can change individual pages by editing their templates. Thus, for example, you can change the home page or about page by editing home/index.html or home/about.html.

For information on the syntax of the templates, refer to the Genshi documentation.