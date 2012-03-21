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
    As of CKAN 1.6.1 custom schema functions apply to both the web user interface
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
