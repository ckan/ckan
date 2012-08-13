Templating Extensions
=====================

Extensions can define their own templates within the template directory.
For example here we have a map extension:

::

    ckanext-map
      ckanext
        map
          public
            javascript/map.js
          templates
            map/snippets/my-snippet.html
            map/snippets/my-snippet-scripts.html
          plugins.py
      setyp.py

The contents of a snippet can be any fragment of HTML using the Jinja
templating language:

::

    {# my-snippet.html #}
    <p>This is my map snippet</p>

    {# my-snippet-scripts.html #}
    <script src="{% url_for_static='/javascript/map.js' %}"></script>

Theme Extensions
----------------

For the latest version of CKAN we’ve split up extensions into two
categories, theme extensions and functional extensions. Themes generally
override large portions of the template files whereas functional ones
simply add small snippets for features.

For example of a theme we may have a demo extension:

::

    ckanext-demo
      ckanext
        demo
          templates
            package/read.html
          plugins.py
      setyp.py

The demo theme needs to extend the core CKAN dataset page to add it’s
map extension. It creates a package/read.html (in the Genshi version of
CKAN this would completely override the template with Jinja we can
simply modify it).

We can use the {% ckan\_extends %} tag to render a core CKAN template
and add our own html to it:

::

    {# Extend the core CKAN template #}
    {% ckan_extends %}

    {# Extend the primary content area of the page #}
    {% block primary_content %}
      {# Super loads in the parent HTML #}
      {{ super() }}

      {# Now we include our map snippet #}
      {% snippet "map/snippets/my-snippet.html" #}
    {% endblock %}

    {# Now we include our scripts #}
    {% block scripts %}
      {{ super() }}

      {% snippet "snippets/my-snippet-scripts.html" %}
    {% endblock %}

There are many blocks available for extension. At the moment these can
be found by looking at the parent page, page.html and base.html.

Functional Extensions
---------------------

Extensions that only provide small snippets that are intended to be
inserted into pages can do so using ``{% ckan_extends %}``.

Firstly any html that is to be inserted into a page should be created
within a snippet. A helper function should then be defined to render
this snippet into the page. See the disqus plugin for an example.

Developers can then take advantage of the recursive nature of the
``{% ckan_extends %}`` tag and override the page that they think the
extension is most likely to be used in.

For example the disqus extension adds a comment block to the
dataset/package read page.

::

    {# Template: disqus/templates/package/read.html #}
    {% ckan_extends %}

    {# Extend the primary content block and call super() to load parent html #} 
    {% block primary_content %}
      {{ super() }}

      {# Now render the comments in out own block #}
      {% block disqus_comments %}
        {{ h.disqus_comments() }}
      {% endblock %}
    {% endblock %}

Because we inserted the HTML within our own block it gives theme
templates the opportunity to remove/expand it. For example if we wish to
remove the comments in our own theme and add them to the sidebar we can.

::

    {# Template: demo/templates/package/read.html #}
    {% ckan_extends %}

    {# Remove the predefined block #}
    {% block disqus_comments %}{% endblock %}

    {# Add it to the sidebar #}
    {% block sidebar_content %}
      {{ super() }}
      {{ h.disqus_comments() }}
    {% endblock %}
