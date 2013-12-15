============================
Adding custom fields to CKAN
============================

CKAN by default allows users to enter custom fields and values into datasets in
the "Additional Information" step when creating datasets and when editing
datasets as additional key-value pairs. This tutorial shows you how to
customize this handling so that your metadata is more integrated with the form
and API. In this tutorial we are assuming that you have read the
:doc:`/extensions/tutorial`

Adding custom fields to packages
--------------------------------

Create a new plugin named ``ckanext-extrafields`` and create a class named
``ExampleIDatasetForms`` inside 
``ckanext-extrafields/ckanext/extrafields/plugins.py`` that implements the 
``IDatasetForm`` interface and inherits from ``SingletonPlugin`` and 
``DefaultDatasetForm``, we will want to implement that functions that allow us 
to update CKAN's default package schema to include our custom field.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :end-before: def create_package_schema(self):

Updating the CKAN schema
^^^^^^^^^^^^^^^^^^^^^^^^

The ``create_package_schema`` function is used whenever a new package is
created, we'll want update the default schema and insert our custom field here.
We will fetch the default schema defined in 
``in default_create_package_schema`` by running ``create_package_schema``'s
super function and update it.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :pyobject: ExampleIDatasetForm.create_package_schema

The CKAN schema is a dictionary where the key is the name of the field and the
value is a list of validators and converters. Here we have a validator to tell
CKAN to not raise a validation error if the value is missing and a converter to
convert the value to and save as an extra. We will want to change the
``update_package_schema`` function with the same update code

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :pyobject: ExampleIDatasetForm.update_package_schema

The ``show_package_schema`` is used when the ``package_show`` action is called,
we want the default_show_package_schema to be updated to include our custom
field. This time, instead of converting to an an extras field. We want our
field to be converted *from* an extras field. So we want to use the
``convert_from_extras`` converter.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :emphasize-lines: 4
    :pyobject: ExampleIDatasetForm.show_package_schema


Package types
^^^^^^^^^^^^^

The ``package_types`` function defines a list of package types that this plugin
handles. Each package has a field containing it's type. Plugins can register to
handle specific types of packages and ignore others. Since our plugin is not
for any specific type of package and we want our plugin to be the default
handler, we update the plugin code to contain the following

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :lines: 34-

Updating templates
^^^^^^^^^^^^^^^^^^

In order for our new field to be visible on the CKAN front-end, we need to
update the templates. Add an additional line to make the plugin implement the
IConfigurer interface

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v2.py
    :emphasize-lines: 3
    :start-after: import ckan.plugins.toolkit as tk
    :end-before: def create_package_schema(self):

This interface allows to implement a function ``update_config`` that allows us
to update the CKAN config, in our case we want to add an additional location
for CKAN to look for templates. Add the following code to your plugin. 

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v2.py
    :pyobject: ExampleIDatasetForm.update_config

You will also need to add a directory under your extension directory to store
the templates. Create a directory called 
``ckanext-extrafields/ckanext/extrafields/templates/`` and the subdirectories
``ckanext-extrafields/ckanext/extrafields/templates/package/snippets/``.

We need to override a few templates in order to get our custom field rendered.
Firstly we need to remove the default custom field handling. Create a template
file in our templates directory called 
``package/snippets/package_metadata_fields.html`` containing

    
.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/package_metadata_fields.html
    :language: jinja
    :end-before: {% block package_metadata_fields %}

This overrides the custom_fields block with an empty block so the default CKAN
custom fields form does not render. Next add a template in our template 
directory called ``package/snippets/package_basic_fields.html`` containing

.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/package_basic_fields.html
    :language: jinja

This adds our custom_text field to the editing form. Finally we want to display
our custom_text field on the dataset page. Add another file called 
``package/snippets/additional_info.html`` containing


.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/additional_info.html
    :language: jinja

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

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v3.py
    :start-after: p.implements(p.IDatasetForm)
    :end-before: def show_package_schema(self):

Tag vocabularies
----------------
If you need to add a custom field where the input options are restrcited to a
provide list of options, you can use tag vocabularies `/tag-vocabularies`. We
will need to create our vocabulary first. By calling vocabulary_create. Add a
function to your plugin.py above your plugin class.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v4.py
    :pyobject: create_country_codes

This codeblock is taken from the ``example_idatsetform plugin``.
``create_country_codes`` tries to fetch the vocabulary country_codes using
``vocabulary_show``. If it is not found it will create it and iterate over
the list of countries 'uk', 'ie', 'de', 'fr', 'es'. For each of these
a vocabulary tag is created using ``tag_create``, belonging to the vocabulary
``country_code``. 

Although we have only defined five tags here, additional tags can be created
at any point by a sysadmin user by calling ``tag_create`` using the API or action
functions. Add a second function below ``create_country_codes``

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v4.py
    :pyobject: country_codes

country_codes will call ``create_country_codes`` so that the ``country_codes``
vocabulary is created if it does not exist. Then it calls tag_list to return
all of our vocabulary tags together. Now we have a way of retrieving our tag
vocabularies and creating them if they do not exist. We just need our plugin
to call this code.  

Adding tags to the schema
^^^^^^^^^^^^^^^^^^^^^^^^^
Update ``_modify_package_schema`` and ``show_package_schema``

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v4.py
    :start-after: return {'country_codes': country_codes}
    :end-before: def create_package_schema(self):
    :emphasize-lines: 8,19-24

We are adding our tag to our plugin's schema. A converter is required to
convert the field in to our tag in a similar way to how we converted our field
to extras earlier. In ``show_package_schema`` we convert from the tag back again
but we have an additional line with another converter containing 
``free_tags_only``. We include this line so that vocab tags are not shown mixed
with normal free tags.

Adding tags to templates
^^^^^^^^^^^^^^^^^^^^^^^^

Add an additional plugin.implements line to to your plugin
to implement the ``ITemplateHelpers``, we will need to add a ``get_helpers``
function defined for this interface.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v4.py
    :start-after: p.implements(p.IConfigurer)
    :end-before: def _modify_package_schema(self, schema):

Our intention here is to tie our country_code fetching/creation to when they
are used in the templates. Add the code below to
``package/snippets/package_metadata_fields.html``

.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/package_metadata_fields.html
    :language: jinja
    :start-after: {% endblock %}


This adds our country code to our template, here we are using the additional
helper country_codes that we defined in our get_helpers function in our plugin.

Adding custom fields to resources
---------------------------------

In order to customize the fields in a resource the schema for resources needs
to be modified in a similar way to the packages. The resource schema
is nested in the package dict as package['resources']. We modify this dict in
a similar way to the package schema. Change ``_modify_package_schema`` to the 
following.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v5.py
    :pyobject: ExampleIDatasetForm._modify_package_schema
    :emphasize-lines: 10-12

Update ``show_package_schema`` similarly

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v5.py
    :pyobject: ExampleIDatasetForm.show_package_schema
    :emphasize-lines: 14-16
        
Save and reload your development server

.. topic:: Details

   CKAN will take any additional keys from the resource schema and save
   them the it's extras field. This is a Postgres Json datatype field, 
   The templates will automatically check this field and display them in the 
   resource_read page.
