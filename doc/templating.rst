Templating
==========

Within CKAN 2.0 we moved out templating to use Jinja2 from Genshi. This was
done to provide a more flexible, extensible and most importantly easy to
understand templating language.

Some useful links to get you started.

-  `Jinja2 Homepage <http://Jinja2.pocoo.org>`_
-  `Jinja2 Developer Documentation <http://Jinja2.pocoo.org/docs/>`_
-  `Jinja2 Template
   Documentation <http://Jinja2.pocoo.org/docs/templates/>`_

Legacy Templates
----------------

Existing Genshi templates have been moved to the *templates\_legacy*
directory and will continue to be served if no file with the same name
is located in *templates*. This should ensure backward compatibility
until instances are able to upgrade to the new system.

The lookup path for templates is as follows. Give the template path
"user/index.html":

1. Look in the template directory of each loaded extension.
2. Look in the template\_legacy directory for each extension.
3. Look in the main ckan template directory.
4. Look in the template\_legacy directory.

CKAN will automatically determine the template engine to use.

File Structure
--------------

The file structure for the CKAN templates is pretty much the same as
before with a directory per controller and individual files per action.

With Jinja2 we also have the ability to use snippets which are small
fragments of HTML code that can be pulled in to any template. These are
kept in a snippets directory within the same folder as the actions that
are using them. More generic snippets are added to templates/snippets.

::

    templates/
      base.html             # A base template with just core HTML structure
      page.html             # A base template with default page layout
      header.html           # The site header.
      footer.html           # The site footer.
      snippets/             # A folder of generic sitewide snippets
      home/
        index.html          # Template for the index action of the home controller
        snippets/           # Snippets for the home controller
      user/
        ...
    templates_legacy/
      # All ckan templates

Using the templating system
---------------------------

Jinja2 makes heavy use of template inheritance to build pages. A template
for an action will tend to inherit from *page.html*:

::

    {% extends "page.html" %}

Each parent defines a number of blocks that can be overridden to add
content to the page. *page.html* defines majority of the markup for a
standard page. Generally only ``{% block primary_content %}`` needs to
be extended:

::

    {% extends "page.html" %}

    {% block page_content.html %}
      <h1>My page title</h1>
      <p>This content will be added to the page</p>
    {% endblock %}

Most template pages will define enough blocks so that the extending page
can customise as little or as much as required.

Internationalisation
--------------------

Jinja2 provides a couple of helpers for
`internationalisation <http://Jinja2.pocoo.org/docs/templates/#i18n>`_.
The most common is to use the ``_()`` function:

::

    {% block page_content.html %}
      <h1>{{ _('My page title') }}</h1>
      <p>{{ _('This content will be added to the page') }}</p>
    {% endblock %}

Variables can be provided using the "format" function:

::

    {% block page_content.html %}
      <p>{{ _('Welcome to CKAN {name}').format(name=username) }}</p>
    {% endblock %}

For longer multiline blocks the ``{% trans %}`` block can be used.

::

    {% block page_content.html %}
      <p>
        {% trans name=username %}
          Welcome to CKAN {{ name }}
        {% endtrans %}
      </p>
    {% endblock %}

Conventions
-----------

There are a few common conventions that have evolved from using the
language.

Includes
~~~~~~~~

.. Note::
    Includes should be avoided as they are not portable use {% snippet %}
    tags whenever possible.

Snippets of text that are included using ``{% include %}`` should be
kept in a directory called _snippets_. This should be kept in the same
directory as the code that uses it.

Generally we use the ``{% snippet %}`` helper in all theme files unless
the parents context must absolutely be available to the snippet. In which
case the usage should be clearly documented.

Snippets
~~~~~~~~

.. Note::
    {% snippet %} tags should be used in favour of h.snippet()

Snippets are essentially middle ground between includes and macros in
that they are includes that allow a specific context to be provided
(includes just receive the parent context).

These should be preferred to includes at all times as they make debugging
much easier.

Macros
~~~~~~

Macros should be used very sparingly to create custom generators for
very generic snippets of code. For example macros/form.html has macros
for creating common form fields.

They should generally be avoided as they are hard to extend and
customise.

Templating within extensions
----------------------------

When you need to add or customize a template from within an extension you need
to tell CKAN that there is a template directory that it can call from. Within
your ``update_config`` method for the extension you'll need to add a
``extra_template_paths`` to the ``config``.

Custom Control Structures
-------------------------

We've provided a few additional control structures to make working with
the templates easier. Other helpers can still be used using the ``h``
object as before.

ckan\_extends
~~~~~~~~~~~~~

::

    {% ckan_extends %}

This works in a very similar way to ``{% extend %}`` however it will
load the next template up in the load path with the same name.

For example if you wish to remove the breadcrumb from the user profile
page in your own site. You would locate the template you wish to
override.

::

    ckan/templates/user/read.html

And create a new one in your theme extension.

::

    ckanext-mytheme/ckanext/mytheme/templates/user/read.html

In this new file you would pull in the core template using
``{% ckan_extends %}``:

::

    {% ckan_extends %}

This will now render the current user/read page but we can override any
portion that we wish to change. In this case the ``breadcrumb`` block.

::

    {% ckan_extends %}

    {# Remove the breadcrumb #}
    {% block breadcrumb %}{% endblock %}

This function works recursively and so is ideal for extensions that wish to
add a small snippet of functionality to the page.

.. Note::
    {% ckan_extend %} only extends templates of the same name.

snippet
~~~~~~~

::

    {% snippet [filepath], [arg1=arg1], [arg2=arg2]... %}

Snippets work very much like Jinja2's ``{% include %}`` except that that
do not inherit the parent templates context. This means that all
variables must be explicitly passed in to the snippet. This makes
debugging much easier.

::

    {% snippet "package/snippets/package_form.html", data=data, errors=errors %}

url\_for
~~~~~~~~

::

    {% url_for [arg1=arg1], [arg2=arg2]... %}

Works exactly the same as ``h.url_for()``:

::

    <a href="{% url_for controller="home", action="index" %}">Home</a>

link\_for
~~~~~~~~~

::

    {% link_for text, [arg1=arg1], [arg2=arg2]... %}

Works exactly the same as ``h.link_for()``:

::

    <li>{% link_for _("Home"), controller="home", action="index" %}</li>

url\_for\_static
~~~~~~~~~~~~~~~~

::

    {% url_for_static path %}

Works exactly the same as ``h.url_for_static()``:

::

    <script src="{% url_for_static "/javascript/home.js" %}"></script>

Form Macros
-----------

For working with forms we have provided some simple macros for
generating common fields. These will be suitable for most forms but
anything more complicated will require the markup to be written by hand.

The macros can be imported into the page using the ``{% import %}``
command.

::

    {% import 'macros/form.html' as form %}

The following fields are provided:

form.input()
~~~~~~~~~~~~

Creates all the markup required for an input element. Handles matching
labels to inputs, error messages and other useful elements.

::

    name        - The name of the form parameter.
    id          - The id to use on the input and label. Convention is to prefix with 'field-'.
    label       - The human readable label.
    value       - The value of the input.
    placeholder - Some placeholder text.
    type        - The type of input eg. email, url, date (default: text).
    error       - A list of error strings for the field or just true to highlight the field.
    classes     - An array of classes to apply to the control-group.

Examples:

::

    {% import 'macros/form.html' as form %}
    {{ form.input('title', label=_('Title'), value=data.title, error=errors.title) }}

form.checkbox()
~~~~~~~~~~~~~~~

Builds a single checkbox input.

::

    name        - The name of the form parameter.
    id          - The id to use on the input and label. Convention is to prefix with 'field-'.
    label       - The human readable label.
    value       - The value of the input.
    checked     - If true the checkbox will be checked
    error       - An error string for the field or just true to highlight the field.
    classes     - An array of classes to apply to the control-group.

Example:

::

    {% import 'macros/form.html' as form %}
    {{ form.checkbox('remember', checked=true) }}

form.select()
~~~~~~~~~~~~~

Creates all the markup required for an select element. Handles matching
labels to inputs and error messages.

A field should be a dict with a "value" key and an optional "text" key
which will be displayed to the user.
``{"value": "my-option", "text": "My Option"}``. We use a dict to easily
allow extension in future should extra options be required.

::

    name        - The name of the form parameter.
    id          - The id to use on the input and label. Convention is to prefix with 'field-'.
    label       - The human readable label.
    options     - A list/tuple of fields to be used as <options>.
    selected    - The value of the selected <option>.
    error       - A list of error strings for the field or just true to highlight the field.
    classes     - An array of classes to apply to the control-group.

Examples:

::

    {% import 'macros/form.html' as form %}
    {{ form.select('year', label=_('Year'), options={'value': 2010, 'value': 2011}, selected=2011, error=errors.year) }}

form.textarea()
~~~~~~~~~~~~~~~

Creates all the markup required for a plain textarea element. Handles
matching labels to inputs, selected item and error messages.

::

    name        - The name of the form parameter.
    id          - The id to use on the input and label. Convention is to prefix with 'field-'.
    label       - The human readable label.
    value       - The value of the input.
    placeholder - Some placeholder text.
    error       - A list of error strings for the field or just true to highlight the field.
    classes     - An array of classes to apply to the control-group.

Examples:

::

    {% import 'macros/form.html' as form %}
    {{ form.textarea('desc', id='field-description', label=_('Description'), value=data.desc, error=errors.desc) }}

form.markdown()
~~~~~~~~~~~~~~~

Creates all the markup required for a Markdown textarea element. Handles
matching labels to inputs, selected item and error messages.

::

    name        - The name of the form parameter.
    id          - The id to use on the input and label. Convention is to prefix with 'field-'.
    label       - The human readable label.
    value       - The value of the input.
    placeholder - Some placeholder text.
    error       - A list of error strings for the field or just true to highlight the field.
    classes     - An array of classes to apply to the control-group.

Examples:

::

    {% import 'macros/form.html' as form %}
    {{ form.markdown('desc', id='field-description', label=_('Description'), value=data.desc, error=errors.desc) }}

form.prepend()
~~~~~~~~~~~~~~

Creates all the markup required for an input element with a prefixed
segment. These are useful for showing url slugs and other fields where
the input information forms only part of the saved data.

::

    name        - The name of the form parameter.
    id          - The id to use on the input and label. Convention is to prefix with 'field-'.
    label       - The human readable label.
    prepend     - The text that will be prepended before the input.
    value       - The value of the input.
                  which will use the name key as the value.
    placeholder - Some placeholder text.
    error       - A list of error strings for the field  or just true to highlight the field.
    classes     - An array of classes to apply to the control-group.

Examples:

::

    {% import 'macros/form.html' as form %}
    {{ form.prepend('slug', id='field-slug', prepend='/dataset/', label=_('Slug'), value=data.slug, error=errors.slug) }}

form.custom()
~~~~~~~~~~~~~

Creates all the markup required for an custom key/value input. These are
usually used to let the user provide custom meta data. Each "field" has
three inputs one for the key, one for the value and a checkbox to remove
it. So the arguments for this macro are nearly all tuples containing
values for the (key, value, delete) fields respectively.

::

    name        - A tuple of names for the three fields.
    id          - An id string to be used for each input.
    label       - The human readable label for the main label.
    values      - A tuple of values for the (key, value, delete) fields. If delete
                  is truthy the checkbox will be checked.
    placeholder - A tuple of placeholder text for the (key, value) fields.
    error       - A list of error strings for the field or just true to highlight the field.
    classes     - An array of classes to apply to the control-group.

Examples:

::

    {% import 'macros/form.html' as form %}
    {{ form.custom(
         names=('custom_key', 'custom_value', 'custom_deleted'),
         id='field-custom',
         label=_('Custom Field'),
         values=(extra.key, extra.value, extra.deleted),
         error='')
    }}

form.autoform()
~~~~~~~~~~~~~~~

Builds a form from the supplied form_info list/tuple.

::

    form_info       - A list of dicts describing the form field to build.
    data            - The form data object.
    errors          - The form errors object.
    error_summary   - The form errors object.

Example

::

    {% set form_info = [
        {'name': 'ckan.site_title', 'control': 'input', 'label': _('Site Title'), 'placeholder': ''},
        {'name': 'ckan.main_css', 'control': 'select', 'options': styles, 'label': _('Style'), 'placeholder': ''},
        {'name': 'ckan.site_description', 'control': 'input', 'label': _('Site Tag Line'), 'placeholder': ''},
        {'name': 'ckan.site_logo', 'control': 'input', 'label': _('Site Tag Logo'), 'placeholder': ''},
        {'name': 'ckan.site_about', 'control': 'markdown', 'label': _('About'), 'placeholder': _('About page text')},
        {'name': 'ckan.site_intro_text', 'control': 'markdown', 'label': _('Intro Text'), 'placeholder': _('Text on home page')},
        {'name': 'ckan.site_custom_css', 'control': 'textarea', 'label': _('Custom CSS'), 'placeholder': _('Customisable css inserted into the page header')},
        ] %}

    {% import 'macros/form.html' as form %}
    {{ form.autoform(form_info, data, errors) }}
