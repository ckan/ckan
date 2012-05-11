================
Tag vocabularies
================

.. versionadded:: 1.7

CKAN tags can belong to a vocabulary, which is a way of grouping related tags together.

Properties
----------

* A CKAN instance can have any number of vocabularies.
* Each vocabulary consists of an ID, name and description.
* Each tag can be assigned to a single vocabulary (or have no vocabulary).
* A dataset can have more than one tag from the same vocabulary, and can have tags from more than one vocabulary.
* Vocabularies can be of two types:
    * Controlled: the list of possible tags is pre-defined
    * Free: users enter their own terms

Using Vocabularies
------------------

A CKAN developer/sysadmin user will have to do a number of things to add some custom vocabs to their CKAN instance:

1. Call CKAN API functions to add the vocabularies and terms to the db.
2. Implement a CKAN extension (with a custom form), including the tag vocabularies in the schema.
3. Provide dataset view, edit and create templates with the new schemas in them.

1. Adding Vocabularies
~~~~~~~~~~~~~~~~~~~~~~

This needs to be done via the action API (:doc:`apiv3`). Please check the examples section to see which calls are needed.

2. Custom Form Schema
~~~~~~~~~~~~~~~~~~~~~

* Make a plugin that implements ``IDatasetForm`` (for example, see ``ExampleDatasetForm`` in https://github.com/okfn/ckanext-example/blob/master/ckanext/example/forms.py).
* Override  ``form_to_db_schema``. Add a new field for your vocabulary tags, making sure that it uses the ``convert_to_tags`` converter with the name of the vocabulary. For example, the following will add a new field called ``vocab_tags``, with each tag assigned to the vocabulary ``EXAMPLE_VOCAB``::

    def form_to_db_schema(self):
        schema = package_form_schema()
        schema.update({'vocab_tags': [ignore_missing, convert_to_tags('EXAMPLE_VOCAB')]})
        return schema

* Override ``db_to_form_schema``. Add your new field to the schema, making sure that it uses the ``convert_from_tags`` validator. If you don't want the tags with vocabularies to be listed along with normal tags (on the web page or via API calls), then make sure that the normal tags field has the ``free_tags_only`` converter applied. For example::

    def db_to_form_schema(self):
        schema = package_form_schema()
        schema.update({
            'tags': {'__extras': [keep_extras, free_tags_only]},
            'vocab_tags': [convert_from_tags('EXAMPLE_VOCAB'), ignore_missing]
        })
        return schema

3. Adding To Templates
~~~~~~~~~~~~~~~~~~~~~~

* If the vocabulary is restricted, you may want to pass a list of all tags in the vocabulary to the template so that they can be displayed as options in a select (or multi-select) box. This should be done by overriding the ``setup_template_variables`` method in your class that implements ``IDatasetForm``. For example::

    def setup_template_variables(self, context, data_dict=None):
        c.vocab_tags = get_action('tag_list')(context, {'vocabulary_id': 'EXAMPLE_VOCAB'})

* The custom tags must be added to the template in order to be displayed or edited. For fixed vocabularies, we recommend adding them as a multi-select tag and using the JQuery ``Chosen`` plugin (included in CKAN core).


Examples
--------

* An example of how to implement it can be found in the section `Customizing Forms` :ref:`example-geospatial-tags`.

* A complete, working example of a custom form that uses tag vocabularies can be found in the CKAN Example extension (http://github.com/okfn/ckanext-example).
