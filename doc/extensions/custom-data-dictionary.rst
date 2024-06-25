.. _custom-data-dictionary:

==============================================
Customizing the DataStore Data Dictionary Form
==============================================

Extensions can customize the Data Dictionary form, keys available and values
stored for each column using the
:py:class:`~ckanext.datastore.interfaces.IDataDictionaryForm` interface.

.. autoclass:: ckanext.datastore.interfaces.IDataDictionaryForm
   :members:

Let's add five new keys with custom validation rules to the data dictionary
fields.

With this plugin enabled each field in the Data Dictionary form will have
an input for:

 - an integer value
 - a JSON object
 - a numeric value that can only be increased when edited
 - a "sticky" value that will not be removed if left blank
 - a secret value that will be stored but never displayed in the form.

First extend the form template to render the form inputs:

.. literalinclude:: ../../ckanext/example_idatadictionaryform/templates/datastore/snippets/dictionary_form.html

We use the ``form.input`` macro to render the form fields. The name
of each field starts with ``fields__`` and includes a ``position`` index
because this block will be rendered once for every field in the data
dictionary.

The value for each input is set to either the value from ``data`` the text
data passed when re-rendering a form containing errors, or ``field`` the
json value (text, number, object etc.) currently stored in the data
dictionary when rendering a form for the first time.

The error for each field is set from ``errors``.

Next we create a plugin to apply the template and validation rules for each
data dictionary field key.

.. literalinclude:: ../../ckanext/example_idatadictionaryform/plugin.py

In ``update_datastore_create_schema`` the ``to_datastore_plugin_data`` factory
generates a validator that will store our new keys as plugin data.
The string passed is used to group keys for this plugin to allow multiple
separate ``IDataDictionaryForm`` plugins to store data for Data Dictionary
fields at the same time. It's possible to use multiple groups from the same
plugin: here we use a different group for the ``secret`` key because we want
to treat it differently.

In ``update_datastore_info_field`` we can add keys stored as plugin data
to the ``fields`` objects returned by ``datastore_info``. Here we add
everything but the ``secret`` key. These values are also passed to the
form template above as ``field``.
