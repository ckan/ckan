===================================================================
Customizing dataset and resource metadata fields using IDatasetForm
===================================================================

Storing additional metadata for a dataset beyond the default metadata in CKAN
is a common use case. CKAN provides a simple way to do this by allowing you to
store arbitrary key/value pairs against a dataset when creating or updating the
dataset. These appear under the "Additional Information" section on the web
interface and in 'extras' field of the JSON when accessed via the API.

Default extras can only take strings for their keys and values, no
validation is applied to the inputs and you cannot make them mandatory or
restrict the possible values to a defined list. By using CKAN's IDatasetForm
plugin interface, a CKAN plugin can add custom, first-class metadata fields to
CKAN datasets, and can do custom validation of these fields.

.. seealso::

   In this tutorial we are assuming that you have read the
   :doc:`/extensions/tutorial`.

   You may also want to check the [ckanext-scheming](https://github.com/ckan/ckanext-scheming) 
   extension, as it will allow metadata schema configuration using a YAML or JSON 
   schema description, replete with custom validation and template snippets for 
   editing and display.

CKAN schemas and validation
---------------------------
When a dataset is created, updated or viewed, the parameters passed to CKAN
(e.g. via the web form when creating or updating a dataset, or posted to an API
end point) are validated against a schema. For each parameter, the schema will
contain a corresponding list of functions that will be run against the value of
the parameter. Generally these functions are used to validate the value
(and raise an error if the value fails validation) or convert the value to a
different value.

For example, the schemas can allow optional values by using the
:func:`~ckan.lib.navl.validators.ignore_missing` validator or check that a
dataset exists using :func:`~ckan.logic.validators.package_id_exists`. A list
of available validators can be found at the :doc:`validators`.
You can also define your own :ref:`custom-validators`.

We will be customizing these schemas to add our additional fields. The
:py:class:`~ckan.plugins.interfaces.IDatasetForm` interface allows us to
override the schemas for creation, updating and displaying of datasets.

.. autosummary::

   ~ckan.plugins.interfaces.IDatasetForm.create_package_schema
   ~ckan.plugins.interfaces.IDatasetForm.update_package_schema
   ~ckan.plugins.interfaces.IDatasetForm.show_package_schema
   ~ckan.plugins.interfaces.IDatasetForm.is_fallback
   ~ckan.plugins.interfaces.IDatasetForm.package_types

CKAN allows you to have multiple IDatasetForm plugins, each handling different
dataset types. So you could customize the CKAN web front end, for different
types of datasets. In this tutorial we will be defining our plugin as the
fallback plugin. This plugin is used if no other IDatasetForm plugin is found
that handles that dataset type.

The IDatasetForm also has other additional functions that allow you to
provide a custom template to be rendered for the CKAN frontend, but we will
not be using them for this tutorial.

Adding custom fields to datasets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a new plugin named ``ckanext-extrafields`` and create a class named
``ExampleIDatasetFormPlugins`` inside
``ckanext-extrafields/ckanext/extrafields/plugin.py`` that implements the
``IDatasetForm`` interface and inherits from ``SingletonPlugin`` and
``DefaultDatasetForm``.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :end-before: def create_package_schema(self):

Updating the CKAN schema
^^^^^^^^^^^^^^^^^^^^^^^^

The :py:meth:`~ckan.plugins.interfaces.IDatasetForm.create_package_schema`
function is used whenever a new dataset is created, we'll want update the
default schema and insert our custom field here.  We will fetch the default
schema defined in
:py:func:`~ckan.logic.schema.default_create_package_schema` by running
:py:meth:`~ckan.plugins.interfaces.IDatasetForm.create_package_schema`'s
super function and update it.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :pyobject: ExampleIDatasetFormPlugin.create_package_schema

The CKAN schema is a dictionary where the key is the name of the field and the
value is a list of validators and converters. Here we have a validator to tell
CKAN to not raise a validation error if the value is missing and a converter to
convert the value to and save as an extra. We will want to change the
:py:meth:`~ckan.plugins.interfaces.IDatasetForm.update_package_schema` function
with the same update code.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :pyobject: ExampleIDatasetFormPlugin.update_package_schema

The :py:meth:`~ckan.plugins.interfaces.IDatasetForm.show_package_schema` is used
when the :py:func:`~ckan.logic.action.get.package_show` action is called, we
want the default_show_package_schema to be updated to include our custom field.
This time, instead of converting to an extras field, we want our field to be
converted *from* an extras field. So we want to use the
:py:meth:`~ckan.logic.converters.convert_from_extras` converter.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v1.py
    :emphasize-lines: 4
    :pyobject: ExampleIDatasetFormPlugin.show_package_schema


Dataset types
^^^^^^^^^^^^^

The :py:meth:`~ckan.plugins.interfaces.IDatasetForm.package_types` function
defines a list of dataset types that this plugin handles. Each dataset has a
field containing its type. Plugins can register to handle specific types of
dataset and ignore others. Since our plugin is not for any specific type of
dataset and we want our plugin to be the default handler, we update the plugin
code to contain the following:

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

This interface allows to implement a function
:py:meth:`~ckan.plugins.interfaces.IDatasetForm.update_config` that allows us
to update the CKAN config, in our case we want to add an additional location
for CKAN to look for templates. Add the following code to your plugin.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v2.py
    :pyobject: ExampleIDatasetFormPlugin.update_config

You will also need to add a directory under your extension directory to store
the templates. Create a directory called
``ckanext-extrafields/ckanext/extrafields/templates/`` and the subdirectories
``ckanext-extrafields/ckanext/extrafields/templates/package/snippets/``.

We need to override a few templates in order to get our custom field rendered.
A common option when using a custom schema is to remove the default custom
field handling that allows arbitrary key/value pairs. Create a template
file in our templates directory called
``package/snippets/package_metadata_fields.html`` containing


.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/package_metadata_fields.html
    :language: jinja
    :end-before: {% block package_metadata_fields %}

This overrides the custom_fields block with an empty block so the default CKAN
custom fields form does not render.


.. versionadded:: 2.3

    Starting from CKAN 2.3 you can combine free extras with custom fields
    handled with ``convert_to_extras`` and ``convert_from_extras``. On prior
    versions you'll always need to remove the free extras handling.

Next add a template in our template
directory called ``package/snippets/package_basic_fields.html`` containing

.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/package_basic_fields.html
    :language: jinja

This adds our custom_text field to the editing form. Finally we want to display
our custom_text field on the dataset page. Add another file called
``package/snippets/additional_info.html`` containing


.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/additional_info.html
    :language: jinja

This template overrides the default extras rendering on the dataset page
and replaces it to just display our custom field.

You're done! Make sure you have your plugin installed and setup as in the
`extension/tutorial`. Then run a development server and you should now have
an additional field called "Custom Text" when displaying and adding/editing a
dataset.

Cleaning up the code
^^^^^^^^^^^^^^^^^^^^

Before we continue further, we can clean up the
:py:meth:`~ckan.plugins.interfaces.IDatasetForm.create_package_schema`
and :py:meth:`~ckan.plugins.interfaces.IDatasetForm.update_package_schema`.
There is a bit of duplication that we could remove. Replace the two functions
with:

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v3.py
    :start-after: p.implements(p.IDatasetForm)
    :end-before: def show_package_schema(self):


.. _custom-validators:

Custom validators
-----------------

You may define custom validators in your extensions and
you can share validators between extensions by registering
them with the :py:class:`~ckan.plugins.interfaces.IValidators` interface.

Any of the following objects may be used as validators as part
of a custom dataset, group or organization schema. CKAN's validation
code will check for and attempt to use them in this order:


1. a callable object taking a single parameter: ``validator(value)``

2. a callable object taking four parameters:
   ``validator(key, flattened_data, errors, context)``

3. a callable object taking two parameters
   ``validator(value, context)``


``validator(value)``
^^^^^^^^^^^^^^^^^^^^

The simplest form of validator is a callable taking a single
parameter. For example::

    from ckan.plugins.toolkit import Invalid

    def starts_with_b(value):
        if not value.startswith('b'):
            raise Invalid("Doesn't start with b")
        return value

The ``starts_with_b`` validator causes a validation error for values
not starting with 'b'.
On a web form this validation error would
appear next to the field to which the validator was applied.

``return value`` must be used by validators when accepting data
or the value will be converted to None. This form is useful
for converting data as well, because the return value will
replace the field value passed::

    def embiggen(value):
        return value.upper()

The ``embiggen`` validator will convert values passed to all-uppercase.


``validator(value, context)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Validators that need access to the database or information
about the user may be written as a callable taking two parameters.
``context['session']`` is the sqlalchemy session object and
``context['user']`` is the username of the logged-in user::

    from ckan.plugins.toolkit import Invalid

    def fred_only(value, context):
        if value and context['user'] != 'fred':
            raise Invalid('only fred may set this value')
        return value

Otherwise this is the same as the single-parameter form above.


``validator(key, flattened_data, errors, context)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Validators that need to access or update multiple fields
may be written as a callable taking four parameters.

All fields and errors in a ``flattened`` form are passed to the 
validator. The validator must fetch values from ``flattened_data`` 
and may replace values in ``flattened_data``. The return value 
from this function is ignored.

``key`` is the flattened key for the field to which this validator was
applied. For example ``('notes',)`` for the dataset notes field or
``('resources', 0, 'url')`` for the url of the first resource of the dataset.
These flattened keys are the same in both the ``flattened_data`` and ``errors``
dicts passed.

``errors`` contains lists of validation errors for each field.

``context`` is the same value passed to the two-parameter
form above.

Note that this form can be tricky to use because some of the values in
``flattened_data`` will have had validators applied
but other fields won't. You may add this type of validator to the
special schema fields ``'__before'`` or ``'__after'`` to have them
run before or after all the other validation takes place to avoid
the problem of working with partially-validated data.

The validator has to be registered. Example:

.. literalinclude:: ../../ckanext/example_ivalidators/plugin.py
    :start-after: from ckan.plugins.toolkit import Invalid
    :end-before: def equals_fortytwo(value):

Tag vocabularies
----------------
If you need to add a custom field where the input options are restricted to a
provided list of options, you can use tag vocabularies
:doc:`/maintaining/tag-vocabularies`.
We will need to create our vocabulary first. By calling
:func:`~ckan.logic.action.vocabulary_create`. Add a function to your plugin.py
above your plugin class.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v4.py
    :pyobject: create_country_codes

This code block is taken from the ``example_idatsetform plugin``.
``create_country_codes`` tries to fetch the vocabulary country_codes using
:func:`~ckan.logic.action.get.vocabulary_show`. If it is not found it will
create it and iterate over the list of countries 'uk', 'ie', 'de', 'fr', 'es'.
For each of these a vocabulary tag is created using
:func:`~ckan.logic.action.create.tag_create`, belonging to the vocabulary
``country_code``.

Although we have only defined five tags here, additional tags can be created
at any point by a sysadmin user by calling
:func:`~ckan.logic.action.create.tag_create` using the API or action functions.
Add a second function below ``create_country_codes``

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v4.py
    :pyobject: country_codes

country_codes will call ``create_country_codes`` so that the ``country_codes``
vocabulary is created if it does not exist. Then it calls
:func:`~ckan.logic.action.get.tag_list` to return all of our vocabulary tags
together. Now we have a way of retrieving our tag vocabularies and creating
them if they do not exist. We just need our plugin to call this code.

Adding tags to the schema
^^^^^^^^^^^^^^^^^^^^^^^^^
Update :py:meth:`~ckan.plugins.interfaces.IDatasetForm._modify_package_schema`
and :py:meth:`~ckan.plugins.interfaces.IDatasetForm.show_package_schema`

.. literalinclude:: ../../ckanext/example_idatasetform/plugin_v4.py
    :start-after: return {'country_codes': country_codes}
    :end-before: def create_package_schema(self):
    :emphasize-lines: 9,21-26

We are adding our tag to our plugin's schema. A converter is required to
convert the field in to our tag in a similar way to how we converted our field
to extras earlier. In
:py:meth:`~ckan.plugins.interfaces.IDatasetForm.show_package_schema` we convert
from the tag back again but we have an additional line with another converter
containing
:py:func:`~ckan.logic.converters.free_tags_only`. We include this line so that
vocab tags are not shown mixed with normal free tags.

Adding tags to templates
^^^^^^^^^^^^^^^^^^^^^^^^

Add an additional plugin.implements line to to your plugin
to implement the :py:class:`~ckan.plugins.interfaces.ITemplateHelpers`, we will
need to add a :py:meth:`~ckan.plugins.interfaces.ITemplateHelpers.get_helpers`
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
to be modified in a similar way to the datasets. The resource schema
is nested in the dataset dict as package['resources']. We modify this dict in
a similar way to the dataset schema. Change ``_modify_package_schema`` to the
following.

.. literalinclude:: ../../ckanext/example_idatasetform/plugin.py
    :pyobject: ExampleIDatasetFormPlugin._modify_package_schema
    :emphasize-lines: 14-16

Update :py:meth:`~ckan.plugins.interfaces.IDatasetForm.show_package_schema`
similarly

.. literalinclude:: ../../ckanext/example_idatasetform/plugin.py
    :pyobject: ExampleIDatasetFormPlugin.show_package_schema
    :emphasize-lines: 20-23

Add the code below to ``package/snippets/resource_form.html``

.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/snippets/resource_form.html
    :language: jinja

This adds our custom_resource_text to the editing form of the resources.

Save and reload your development server CKAN will take any additional keys from
the resource schema and save them the its extras field.  The templates will
automatically check this field and display them in the resource_read page.

Sorting by custom fields on the dataset search page
---------------------------------------------------
Now that we've added our custom field, we can customize the CKAN web front end
search page to sort datasets by our custom field. Add a new file called
``ckanext-extrafields/ckanext/extrafields/templates/package/search.html`` containing:

.. literalinclude:: ../../ckanext/example_idatasetform/templates/package/search.html
    :language: jinja
    :emphasize-lines: 16-17

This overrides the search ordering drop down code block, the code is the
same as the default dataset search block but we are adding two additional lines
that define the display name of that search ordering (e.g. Custom Field
Ascending) and the SOLR sort ordering (e.g. custom_text asc). If you reload your
development server you should be able to see these two additional sorting options
on the dataset search page.

The SOLR sort ordering can define arbitrary functions for custom sorting, but
this is beyond the scope of this tutorial for further details see
http://wiki.apache.org/solr/CommonQueryParameters#sort and
http://wiki.apache.org/solr/FunctionQuery


You can find the complete source for this tutorial at
https://github.com/ckan/ckan/tree/master/ckanext/example_idatasetform
