Extensions can define their own templates within the template directory. For
example here we have a map extension::

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
templating language::

  {# my-snippet.html #}
  <p>This is my map snippet</p>

  {# my-snippet-scripts.html #}
  <script src="{% url_for_static='/javascript/map.js' %}"></script>

Templates defined by extensions are not currently inserted automatically into
the main CKAN templates. Instead they require each instance to have a "theme"
or "instance" extension. For example we may have a demo extension::

  ckanext-demo
    ckanext
      demo
        templates
          package/read.html
        plugins.py
    setyp.py

The demo theme needs to extend the core CKAN dataset page to add it's map
extension. It creates a package/read.html (in the Genshi version of CKAN this
would completely override the template with Jinja we can simply modify it).

We can use the "ckan_extends" tag to render a core CKAN template and add our
own html to it::

  {# Extend the core CKAN template #}
  {% ckan_extends 'package/read.html' %}

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

There are many blocks available for extension. At the moment these can be found
by looking at the parent page, page.html and base.html.
