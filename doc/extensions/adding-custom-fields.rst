============================
Adding Custom Fields to CKAN
============================

CKAN by default allows users to enter custom fields and values into datasets in
the "Additional Information" step when creating datasets and when editing
datasets as additional key-value pairs. This tutorial shows you how to
customize this handling so that your metadata is more integrated with the form
and API. In this tutorial we are assuming that you have read the
:doc:`/extensions/tutorial`

Adding Custom Fields to Packages
--------------------------------

Create a new plugin named ``ckanext-extrafields`` and create a class named
``ExtraFieldsPlugins`` inside 
``ckanext-extrafields/ckanext/extrafields/plugins.py`` that implements the 
``IDatasetForm`` interface and inherits from ``SingletonPlugin`` and 
``DefaultDatasetForm``, we will want to implement that functions that allow us 
to update CKAN's default package schema to include our custom field.

.. code-block:: python

    import ckan.plugins as p
    import ckan.plugins.toolkit as tk
    
    class ExtraFieldsPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
        p.implements(p.IDatasetForm)

Updating the CKAN Schema
^^^^^^^^^^^^^^^^^^^^^^^^

The ``create_package_schema`` function is used whenever a new package is
created, we'll want update the default schema and insert our custom field here.
We will fetch the default schema defined in 
``in default_create_package_schema`` by running ``create_package_schema``'s
super function and update it.

.. code-block:: python

    def create_package_schema(self):
        # let's grab the default schema in our plugin
        schema = super(ExtraFieldsPlugin, self).create_package_schema()
        #our custom field
        schema.update({
            'custom_text': [tk.get_validator('ignore_missing'), 
                tk.get_converter('convert_to_extras')]
        })
        return schema

The CKAN schema is a dictionary where the key is the name of the field and the
value is a list of validators and converters. Here we have a validator to tell
CKAN to not raise a validation error if the value is missing and a converter to
convert the value to and save as an extra. We will want to change the
``update_package_schema`` function with the same update code

.. code-block:: python

    def update_package_schema(self):
        schema = super(ExtraFieldsPlugin, self).update_package_schema()
        #our custom field
        schema.update({
            'custom_text': [tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_extras')]
        })
        return schema

The ``show_package_schema`` is used when the ``package_show`` action is called,
we want the default_show_package_schema to be updated to include our custom
field. This time, instead of converting to an an extras field. We want our
field to be converted *from* an extras field. So we want to use the
``convert_from_extras`` converter.


.. code-block:: python
   :emphasize-lines: 4

    def show_package_schema(self):
        schema = super(CustomFieldsPlugins, self).show_package_schema()
        schema.update({
            'custom_text': [tk.get_converter('convert_from_extras'),
                tk.get_validator('ignore_missing')]
        })
        return schema

.. topic :: Database Details 

    By default CKAN is saving the custom values to the package_extra table.
    When a call to ``package_show`` is made, normally the results in
    package_extra are returned as a nested dictionary named 'extras'. 
    By editing the schema in our plugin we are moving the field into the top 
    level of the dictionary returned from ``package_show``. Our custom_field
    will seemlessly appear as part of the schema. This means it appears as a 
    top level attribute for our package in our templates and API calls whilst 
    letting CKAN handle the conversion and saving to the package_extra table. 

Package Types
^^^^^^^^^^^^^

The ``package_types`` function defines a list of package types that this plugin
handles. Each package has a field containing it's type. Plugins can register to
handle specific types of packages and ignore others. Since our plugin is not
for any specific type of package and we want our plugin to be the default
handler, we update the plugin code to contain the following

.. code-block:: python

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

Updating Templates
^^^^^^^^^^^^^^^^^^

In order for our new field to be visible on the CKAN front-end, we need to
update the templates. Add an additional line to make the plugin implement the
IConfigurer interface

.. code-block:: python
   :emphasize-lines: 3
   
    class ExtraFieldsPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
        p.implements(p.IDatasetForm)
        p.implements(p.IConfigurer)

This interface allows to implement a function ``update_config`` that allows us
to update the CKAN config, in our case we want to add an additional location
for CKAN to look for templates. Add the following code to your plugin. 

.. code-block:: python

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        tk.add_template_directory(config, 'templates')

You will also need to add a directory under your extension directory to store
the templates. Create a directory called 
``ckanext-extrafields/ckanext/extrafields/templates/`` and the subdirectories
``ckanext-extrafields/ckanext/extrafields/templates/package/snippets/``.

We need to override a few templates in order to get our custom field rendered.
Firstly we need to remove the default custom field handling. Create a template
file in our templates directory called 
``package/snippets/package_metadata_fields.html`` containing

    
.. code-block:: jinja 

    {% ckan_extends %}
    
    {# Remove 'free extras' from the package form. If you're using
    convert_to/from_extras() as we are with our 'custom_text' field below then
    you need to remove free extras from the form, or editing your custom field
    won't work. #}
    {% block custom_fields %}
    {% endblock %}

This overrides the custom_fields block with an empty block so the default CKAN
custom fields form does not render. Next add a template in our template 
directory called ``package/snippets/package_basic_fields.html`` containing

.. code-block:: jinja 

    {% ckan_extends %}

    {% block package_basic_fields_custom %}
      {{ form.input('custom_text', label=_('Custom Text'), id='field-custom_text', placeholder=_('custom text'), value=data.custom_text, error=errors.custom_text, classes=['control-medium']) }}
    {% endblock %}

This adds our custom_text field to the editing form. Finally we want to display
our custom_text field on the dataset page. Add another file called 
``package/snippets/additional_info.html`` containing


.. code-block:: jinja 

    {% ckan_extends %}

    {% block extras %}
      {% if pkg_dict.custom_text %}
        <tr>
          <th scope="row" class="dataset-label">{{ _("Custom Text") }}</th>
          <td class="dataset-details">{{ pkg_dict.custom_text }}</td>
        </tr>
      {% endif %}
    {% endblock %}

This template overrides the the default extras rendering on the dataset page 
and replaces it to just display our custom field.

You're done! Make sure you have your plugin installed and setup as in the 
`extension/tutorial`. Then run a development server and you should now have 
an additional field called "Custom Text" when displaying and adding/editing a 
dataset.

Cleaning up the code
^^^^^^^^^^^^^^^^^^^^

Before we continue further, we can clean up the ``create_package_schema``
and ``update_package_schema``. There is a bit of duplication that we could
remove. Replace the two functions with

.. code-block:: python

    def _modify_package_schema(self, schema):
        schema.update({
            'custom_text': [tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_extras')]
        })
        return schema

    def create_package_schema(self):
        schema = super(ExtraFieldsPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(ExtraFieldsPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

Tag Vocabularies
----------------
If you need to add a custom field where the input options are restrcited to a
provide list of options, you can use tag vocabularies `/tag-vocabularies`. We
will need to create our vocabulary first. By calling vocabulary_create. Add a
function to your plugin.py above your plugin class.

.. code-block:: python

        def create_country_codes():
            user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
            context = {'user': user['name']}
            try:
                data = {'id': 'country_codes'}
                tk.get_action('vocabulary_show')(context, data)
            except tk.ObjectNotFound:
                data = {'name': 'country_codes'}
                vocab = tk.get_action('vocabulary_create')(context, data)
                for tag in (u'uk', u'ie', u'de', u'fr', u'es'):
                    data = {'name': tag, 'vocabulary_id': vocab['id']}
                    tk.get_action('tag_create')(context, data)

This codeblock is taken from the ``example_idatsetform plugin``.
``create_country_codes`` tries to fetch the vocabulary country_codes using
``vocabulary_show``. If it is not found it will create it and iterate over
the list of countries 'uk', 'ie', 'de', 'fr', 'es'. For each of these
a vocabulary tag is created using ``tag_create``, belonging to the vocabulary
``country_code``. 

Although we have only defined five tags here, additional tags can be created
at any point by a sysadmin user by calling ``tag_create`` using the API or action
functions. Add a second function below ``create_country_codes``

.. code-block:: python

    def country_codes():
        create_country_codes()
        try:
            country_codes = tk.get_action('tag_list')(
                    data_dict={'vocabulary_id': 'country_codes'})
            return country_codes
        except tk.ObjectNotFound:
            return None

country_codes will call ``create_country_codes`` so that the ``country_codes``
vocabulary is created if it does not exist. Then it calls tag_list to return
all of our vocabulary tags together. Now we have a way of retrieving our tag
vocabularies and creating them if they do not exist. We just need our plugin
to call this code.  

Adding Tags to the Schema
^^^^^^^^^^^^^^^^^^^^^^^^^
Update ``_modify_package_schema`` and ``show_package_schema``

.. code-block:: python
   :emphasize-lines: 8,19-24

    def _modify_package_schema(self, schema):
        schema.update({
            'custom_text': [tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_extras')]
        })
        schema.update({
                'country_code': [tk.get_validator('ignore_missing'),
                    tk.get_converter('convert_to_tags')('country_codes')]
                })
        return schema

    def show_package_schema(self):
        schema = super(CustomFieldsPlugins, self).show_package_schema()
        schema.update({
            'custom_text': [tk.get_converter('convert_from_extras'),
                tk.get_validator('ignore_missing')]
        })

        schema['tags']['__extras'].append(tk.get_converter('free_tags_only'))
        schema.update({
            'country_code': [
                tk.get_converter('convert_from_tags')('country_codes'),
                tk.get_validator('ignore_missing')]
            })
        return schema

We are adding our tag to our plugin's schema. A converter is required to
convert the field in to our tag in a similar way to how we converted our field
to extras earlier. In ``show_package_schema`` we convert from the tag back again
but we have an additional line with another converter containing 
``free_tags_only``. We include this line so that vocab tags are not shown mixed
with normal free tags.

Adding Tags to Templates
^^^^^^^^^^^^^^^^^^^^^^^^

Add an additional plugin.implements line to to your plugin
to implement the ``ITemplateHelpers``, we will need to add a ``get_helpers``
function defined for this interface.

.. code-block:: python

    plugins.implements(plugins.ITemplateHelpers, inherit=False)

    def get_helpers(self):
        return {'country_codes': country_codes}

Our intention here is to tie our country_code fetching/creation to when they
are used in the templates. Add the code below to
``package/snippets/package_metadata_fields.html``

.. code-block:: jinja 

    {% block package_metadata_fields %}

      <div class="control-group">
        <label class="control-label" for="field-country_code">{{ _("Country Code") }}</label>
        <div class="controls">
          <select id="field-country_code" name="country_code" data-module="autocomplete">
            {% for country_code in h.country_codes()  %}
              <option value="{{ country_code }}" {% if country_code in data.get('country_code', []) %}selected="selected"{% endif %}>{{ country_code }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      {{ super() }}

    {% endblock %}

This adds our country code to our template, here we are using the additional
helper country_codes that we defined in our get_helpers function in our plugin.

Adding Custom Fields to Resources
---------------------------------

In order to customize the fields in a resource the schema for resources needs
to be modified in a similar way to the packages. The resource schema
is nested in the package dict as package['resources']. We modify this dict in
a similar way to the package schema. Change ``_modify_package_schema`` to the 
following.

.. code-block:: python

    def _modify_package_schema(self, schema):
        schema.update({
            'custom_text': [tk.get_validator('ignore_missing'),
                tk.get_converter('convert_to_extras')]
        })
        schema['resources'].update({
            'custom_resource_text' : [ tk.get_validator('ignore_missing') ]
        })
        return schema

Update ``show_package_schema`` similarly

.. code-block:: python

    def show_package_schema(self):
        schema = super(CustomFieldsPlugins, self).show_package_schema()
        schema.update({
            'custom_text': [tk.get_converter('convert_from_extras'),
                tk.get_validator('ignore_missing')]
        })
        schema['resources'].update({
                'custom_resource_text' : [ tk.get_validator('ignore_missing') ]
        })
        return schema
        
Save and reload your development server

.. topic:: Details

   CKAN will take any additional keys from the resource schema and save
   them the it's extras field. This is a Postgres Json datatype field, 
   The templates will automatically check this field and display them in the 
   resource_read page.
