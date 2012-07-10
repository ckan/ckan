================
Jinja Templating
================

The base theme of CKAN now uses `Jinja <http://jinja.pocoo.org>` as it's
templating engine. Old Genshi templates are still supported but we advise
that you start to move away from using them.

Using the templating system
---------------------------

Jinja makes heavy use of template inheritance to build pages. A template
for an action will tend to inherit from *page.html*::

{% extends "page.html" %}

Each parent defines a number of blocks that can be overridden to add content
to the page. *page.html* defines majority of the markup for a standard
page. Generally only ``{% block primary_content %}`` needs to be extended::

{% extends "page.html" %}

{% block page_content.html %}
  <h1>My page title</h1>
  <p>This content will be added to the page</p>
{% endblock %}

Most template pages will define enough blocks so that the extending page can
customise as little or as much as required.

Conventions
-----------

There are a few common conventions that have evolved from using the language.

Includes
~~~~~~~~

Snippets of text that are included using ``{% include %}`` should be kept in
a directory called *partials*. This should be kept in the same directory
as the code that uses it.

Snippets
~~~~~~~~

Snippets are essentially middle ground between includes and macros in that
they are includes that allow a specific context to be provided (includes just
receive the parent context).

Ideally we should be able to remove one of these from the final release of the
new theme.

Macros
~~~~~~

Macros should be used very sparingly to create custom generators for very
generic snippets of code. For example macros/form.html has macros for creating
common form fields.

They should generally be avoided as they are hard to extend and customise.

Extensions that modify content
------------------------------

Ideally there should only be one extension that modifies the CKAN templates,
we will call these extensions *themes*.

Extensions that insert new content
----------------------------------

Reasoning
---------

Jinja was chosen in an attempt to simplify the templating system and to make
it much easier for people to extend and re-theme CKAN.
