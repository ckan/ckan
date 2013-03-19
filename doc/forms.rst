=================
Customizing Forms
=================

The forms used to edit datasets and groups in CKAN can be customized. This lets you tailor them to your needs, 
helping your users choose from sensible options or use different data formats.  
This document explains how to customize the dataset and group forms you offer to your users. 

.. warning:: This is an advanced topic. Ensure you are familiar with :doc:`extensions` before attempting to customize forms. 
.. note:: 
    This document describes the process for creating dataset forms that is used in the ``ckanext-example`` extension.
    The source code is available at http://github.com/okfn/ckanext-example.
    Group forms can be customised in a similar way, see ``ckanext-example`` again for reference.


Creating a Dataset Form
-----------------------

The recommended way to create a dataset form is by using a CKAN extension. 

First, create a new plugin that implements ``ckan.plugins.IDatasetForm``. It is also useful to implement
``ckan.plugins.IConfigurer`` as well, so that you can add the directory that will contain your new dataset
form template to CKAN's list of template paths.


::

    import ckan.plugins

    class ExampleDatasetForm(ckan.plugins.SingletonPlugin):
        implements(ckan.plugins.IDatasetForm, inherit=True)
        implements(ckan.plugins.IConfigurer, inherit=True)    

Next, create a directory in your CKAN extension to store your HTML template(s) and add 
an ``update_config`` method to make sure that this template is on CKAN's template path. 
Here we add the ``ckanext/example/theme/templates`` directory to the path.

::


    def update_config(self, config):
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        template_dir = os.path.join(rootdir, 'ckanext', 'example', 'theme', 'templates')
        config['extra_template_paths'] = ','.join([
            template_dir, config.get('extra_template_paths', '')
        ])

You can now add your HTML template(s) to the templates directory. It is recommended that you copy
the existing CKAN dataset form (``ckan/templates/package/new_package_form.html``) and make 
modifications to it. However, it is possible to start from scratch.

If you create a template in your extension templates directory at ``package/new_package_form.html``,
it will override the default CKAN template. This applies to any template in the CKAN templates directory.
You can also override them by changing the paths returned by the following methods in your extension:

::

    def package_form(self):
        return 'package/new_package_form.html'

    def new_template(self):
        return 'package/new.html'

    def comments_template(self):
        return 'package/comments.html'

    def search_template(self):
        return 'package/search.html'

    def read_template(self):
        return 'package/read.html'

    def history_template(self):
        return 'package/history.html'

.. note:: The ``package_form`` and ``*_template`` methods (above) are required in order to implement IDatasetForm.

Two other methods must be provided by your extension when implementing the IDatasetForm interface:

::

    def package_types(self):
        return ['dataset']

    def is_fallback(self):
        return True

``package_types`` sets the dataset type associated with your extension, and updates the Pylons routing so
that datasets of this type can be found at the ``/<type>`` URL in your CKAN instance.

For example, changing ``package_type`` to return ``['catalog']`` would mean that any visits to 
``/catalog/new``, ``/catalog/edit``, etc. would use your extension's dataset form, but going to
``/dataset/new``, ``/dataset/edit``, etc. would still return CKAN's default dataset form.

``is_fallback`` means that this extension should be the default dataset type. If ``True``, even when the
return value of ``package_types`` is changed, going to ``/dataset/new`` will still use the
extension's dataset form instead of CKAN's default.


Passing Data to Templates
-------------------------

Your IDatasetForm extension can define a ``_setup_template_variables`` method, and use it to add
data to the Pylons ``c`` object (which is passed to the templates).

For example, you can define ``_setup_template_variables`` as follows:

::

    def setup_template_variables(self, context, data_dict=None, package_type=None):
        from ckan.lib.base import c
        from ckan import model
        c.licences = model.Package.get_license_options()

and then use it in your HTML template:

::

    <dd class="license-field">
      <select id="license_id" name="license_id">
        <py:for each="licence_desc, licence_id in c.licences">
          <option value="${licence_id}">${licence_desc}</option>
        </py:for>
      </select>
    </dd>


Custom Schemas
--------------

.. note::
    As of CKAN 1.7 custom schema functions apply to both the web user interface
    and the API.

    An example of the use of these methods can be found in the ``ckanext-example`` extension.

The data fields that are accepted and returned by CKAN for each dataset can be
changed by an IDatasetForm extension by overriding the following methods:

::

    def form_to_db_schema_options(self, options)

This allows us to select different schemas for different purpose eg via the web interface 
or via the api or creation vs updating. 
It is optional and if not available form_to_db_schema should be used.

::

  _form_to_db_schema(self)

This defines a navl schema to customize validation and conversion to the database.

::

  _db_to_form_schema(self)

This defines a navl schema to customize conversion from the database to the form.

::

  _db_to_form_schema_options(self, options)

Like ``_form_to_db_schema_options()``, this allows different schemas to be
used for different purposes.
It is optional, and if it is not available then ``form_to_db_schema`` is used.


.. _example-geospatial-tags:

Example: Geospatial Tags
------------------------

In this example we look at how create a plugin that adds a new dataset field called ``geographical_coverage``.
This field allows the user to specify one or more country-code tags in order to indicate which
countries are covered by the dataset. Additionally, the tags must be part of a fixed CKAN tag vocabularly
called ``country_codes``.

More information about tag vocabularies can be found in :doc:`tag-vocabularies`.


1. Creating the Tag Vocabulary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First we are going to create the ``country_codes`` vocabulary and add a few tags to it.
The following code can be saved to a python script and then run from the command line.

::

    import json
    import requests

    ckan_url = 'http://127.0.0.1:5000'
    api_key = 'xxxx'

    geo_tags = [u'uk', u'ie', u'de', u'fr', u'es']
    headers = {'Authorization': api_key}

We are going to use the requests module (tested with version 0.10.7, available on PyPI) to make our POST requests.

Replace the values of ``ckan_url`` and ``api_key`` with the URL to your CKAN instance and
your API key respectively. You must be a system administrator in order to create tag
vocabularies.

We also define the 5 tags that we will add to the vocabulary here, and set the ``Authorization`` header
to the value of our API key.

::

    # create the vocabulary
    data = json.dumps({'name': u'country_codes'})
    r = requests.post(ckan_url + '/api/action/vocabulary_create',
                      data=data,
                      headers=headers)
    vocab_id = json.loads(r.text)['result']['id']

This creates our ``country_codes`` vocabulary, and saves a reference to the vocabulary ID that
is returned by CKAN.

::

    # add tags
    for geo_tag in geo_tags:
        data = json.dumps({'name': geo_tag, 'vocabulary_id': vocab_id})
        r = requests.post(ckan_url + '/api/action/tag_create',
                          data=data,
                          headers=headers)

We then add each of our tags, making sure to set their vocabulary ID.


2. Creating the Plugin
~~~~~~~~~~~~~~~~~~~~~~

First we create a CKAN plugin that implements IDatasetForm:

::

    import ckan.plugins

    class GeospatialTagDatasetForm(SingletonPlugin):
        implements(IDatasetForm, inherit=True)

        def package_form(self):
            return 'package/new_package_form.html'

        def new_template(self):
            return 'package/new.html'

        def comments_template(self):
            return 'package/comments.html'

        def search_template(self):
            return 'package/search.html'

        def read_template(self):
            return 'package/read.html'

        def history_template(self):
            return 'package/history.html'

        def is_fallback(self):
            return True

        def package_types(self):
            return ['dataset']

We want to pass the list of country code tags through to our dataset form, so we
define a ``setup_template_variables`` function which stores the tags as a ``geographical_coverage``
against the Pylons ``c`` object.

::

        def setup_template_variables(self, context, data_dict=None, package_type=None):
            try:
                data = {'vocabulary_id': u'country_codes'}
                c.geographical_coverage = get_action('tag_list')(context, data)
            except NotFound:
                c.geographical_coverage = []

Finally we have to update our dataset schema so that we can store the
country code data.

::

    def form_to_db_schema(self, package_type=None):
        from ckan.logic.schema import package_form_schema
        from ckan.lib.navl.validators import ignore_missing
        from ckan.logic.converters import convert_to_tags

        schema = package_form_schema()
        schema.update({
            'geographical_coverage': [ignore_missing, convert_to_tags('country_codes')]
        })
        return schema

    def db_to_form_schema(data, package_type=None):
        from ckan.logic.converters import convert_from_tags, free_tags_only
        from ckan.lib.navl.validators import ignore_missing, keep_extras

        schema = package_form_schema()
        schema.update({
            'tags': {
                '__extras': [keep_extras, free_tags_only]
            },
            'geographical_coverage': [convert_from_tags('country_codes'), ignore_missing],
        })
        return schema

Here were use the ``convert_to_tags`` and ``convert_from_tags`` converters, so that our
country codes are stored as normal CKAN tags. We also apply the ``free_tags_only`` converter
to the ``tags`` field when displaying datasets in order to remove our geospatial tags
from this list and display them separately.


3. Updating the Template
~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    To edit fixed tag vocabulary fields, we recommend using a HTML multiple select tag together
    with the JQuery *Chosen* plugin (included in CKAN core).

You must add a new field to your dataset form in order to display (and edit) the new
geographical coverage tags. The following HTML segment creates a multiple select element
to display the tags, marking any tags that are currently saved as 'selected'.

::

      <select id="geographical_coverage" class="chzn-select"
              name="geographical_coverage" multiple="multiple">
        <py:for each="tag in c.geographical_coverage">
          <py:choose test="">
          <option py:when="tag in data.get('geographical_coverage', [])"
                  selected="selected" value="${tag}">${tag}</option>
          <option py:otherwise="" value="${tag}">${tag}</option>
          </py:choose>
        </py:for>
      </select>
