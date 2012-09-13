===============
Template Blocks
===============

These blocks can be extended by child templates to replace or extend common
CKAN functionality.

Usage
-----

There are currently two base templates *base.html* which provides the bare
HTML structure such as title, head and body tags as well as hooks for adding
links, stylesheets and scripts. *page.html* defines the content structure and
is the template that you'll likely want to use.

To extend a template simply create a new template file and call
``{% extend %}`` then define the blocks that you wish to override.

===================
Blocks in page.html
===================

*page.html* extends the "page" block in *base.html* and provides the basic
page structure for primary and secondary content.

header
------

Override the header on a page by page basis by extending this block. If
making site wide header changes it is preferable to override the header.html
file::

  {% block header %}
    {% include "custom_header.html" %}
  {% endblock %}

content
-------

The content block allows you to replace the entire content section of the page
with your own markup if needed::

  {% block content %}
    <div class="custom-content">
      {% block custom_block %}{% endblock %}
    </div>
  {% endblock %}

toolbar
-------

The toolbar is for content to be added at the top of the page such as the
breadcrumb navigation. You can remove/replace this by extending this block::

  {# Remove the toolbar from this page. #}
  {% block toolbar %}{% endblock %}

breadcrumb
----------

Add a breadcrumb to the page by extending this element::

  {% block breadcrumb %}
    {% include "breadcrumb.html" %}
  {% endblock %}

actions
-------

Add actions to the page by extending this element::

  {% block actions %}
    <a class="btn" href="{{ save_url }}">Save</a>
  {% endblock %}

primary
-------

This block can be used to remove the entire primary content element::

  {% block primary %}{% endblock %}

primary_content
---------------

The primary_content block can be used to add content to the page.  This is the
main block that is likely to be used within a template::

  {% block primary_content %}
    <h1>My page content</h1>
    <p>Some content for the page</p>
  {% endblock %}

secondary
---------

This block can be used to remove the entire secondary content element::

  {% block secondary %}{% endblock %}

secondary_content
-----------------

The secondary_content block can be used to add content to the sidebar of the
page. This is the main block that is likely to be used within a template::

  {% block secondary_content %}
    <h2>A sidebar item</h2>
    <p>Some content for the item</p>
  {% endblock %}

footer
------

Override the footer on a page by page basis by extending this block::

  {% block footer %}
    {% include "custom_footer.html" %}
  {% endblock %}

If making site wide header changes it is preferable to override the
*footer.html*. Adding scripts should use the "scripts" block instead.

===================
Blocks in base.html
===================

doctype
-------

Allows the DOCTYPE to be set on a page by page basis::

  {% block doctype %}<!DOCTYPE html>{% endblock %}

htmltag
-------

Allows custom attributes to be added to the <html> tag::

  {% block htmltag %}<html lang="en-gb" class="no-js">{% endblock %}

headtag
-------

Allows custom attributes to be added to the <head> tag::

  {% block headtag %}<head data-tag="No idea what you'd add here">{% endblock %}

bodytag
-------

Allows custom attributes to be added to the <body> tag::

  {% block bodytag %}<body class="full-page">{% endblock %}

meta
----

Add custom meta tags to the page. Call ``super()`` to get the default tags
such as charset, viewport and generator::

  {% block meta %}
    {{ super() }}
    <meta name="author" value="Joe Bloggs" />
    <meta name="description" value="My website description" />
  {% endblock %}

title
-----

Add a custom title to the page by extending the title block. Call ``super()``
to get the default page title::

  {% block title %}My Subtitle - {{ super() }}{% endblock %}

links
-----

The links block allows you to add additional content before the stylesheets
such as rss feeds and favicons in the same way as the meta block::

  {% block link %}
    <meta rel="shortcut icon" href="custom_icon.png" />
  {% endblock %}

styles
------

The styles block allows you to add additional stylesheets to the page in
the same way as the meta block. Use `` super() `` to include the default
stylesheets before or after your own::

  {% block styles %}
    {{ super() }}
    <link rel="stylesheet" href="/base/css/custom.css" />
  {% endblock %}

page
----

The page block allows you to add content to the page. Most of the time it is
recommended that you extend one of the page.html templates in order to get
the site header and footer. If you need a clean page then this is the
block to use::

  {% block page %}
    <div>Some other page content</div>
  {% endblock %}

scripts
-------

The scripts block allows you to add additonal scripts to the page. Use the
``super()`` function to load the default scripts before/after your own::

  {% block script %}
    {{ super() }}
    <script src="/base/js/custom.js"></script>
  {% endblock %}
