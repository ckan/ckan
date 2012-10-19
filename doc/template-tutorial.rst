Creating a new template
=======================

This is a brief tutorial covering the basics of building a common
template.

Extending a base template
-------------------------

Firstly we need to extend a parent template to provide us with some
basic page structure. This can be any other HTML page however the most
common one is ``page.html`` which provides the full CKAN theme including
header and footer.

::

    {% extends "page.html" %}

The ``page.html`` template provides numerous blocks that can be
extended. It’s worth spending a few minutes getting familiar with what’s
available. The most common blocks that we’ll be using are those ending
with “content”.

-  ``primary_content``: The main content area of the page.
-  ``secondary_content``: The secondary content (sidebar) of the page.
-  ``breadcrumb_content``: The contents of the breadcrumb navigation.
-  ``actions_content``: The content of the actions bar to the left of
   the breadcrumb.

Primary Content
---------------

For now we’ll add some content to the main content area of the page.

::

    {% block primary_content %}
      {{ super() }}

      {% block my_content %}
        <h2>{{ _('This is my content heading') }}</h2>
        <p>{{ _('This is my content') }}</p>
      {% endblock %}
    {% endblock %}

Notice we’ve wrapped our own content in a block. This allows other
templates to extend and possibly override this one and is extremely
useful for making a them more customisable.

Secondary Content
-----------------

Secondary content usually compromises of reusable modules which are
pulled in as snippets. Snippets are also very useful for keeping the
templates clean and allowing theme extensions to override them.

::

    {% block primary_content %}
      {{ super() }}

      {% block my_sidebar_module %}
        {% snippet "snippets/my-sidebar-module.html" %}
      {% endblock %}
    {% endblock %}

Breadcrumb and Actions
----------------------

There is a consistent breadcrumb running through all the pages and often
it is useful to provide additional actions that a related to the page.

::

    {% block breadcrumb_content %}
      <li class="active">{% link_for _('Viewing Dataset'), controller='package', action='read', id=pkg.id %}</li>
    {% endblock %}

    {% block actions_content %}
      {{ super() }}
      <li class="active">{% link_for _('New Dataset'), controller='package', action='new', class_='btn', icon='plus' %}</li>
    {% endblock %}

Scripts and Stylesheets
-----------------------

Currently scripts and stylesheets can be added by extending the
``styles`` and ``scripts`` blocks. This is soon to be replaced with the
``{% resource %}`` tag which manages script loading for us.

::

    {% block styles %}
      {{ super() }}
      <link rel="stylesheet" href="{% url_for_static "my-style.css" %}" />
    {% endblock %}

    {% block scripts %}
      {{ super() }}
      <script src="{% url_for_static "my-script.js" %}"></script>
    {% endblock %}

Summary
-------

And that’s about all there is to it be sure to check out ``base.html``
and ``page.html`` to see all the tags available for extension.
