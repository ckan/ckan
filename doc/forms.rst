=================
Customizing Forms
=================

The forms used to edit datasets and groups in CKAN can be customized. This lets you tailor them to your needs, helping your users choose from sensible options or use different data formats. 

This document explains how to customize the dataset and group forms you offer to your users, without getting embroiled in the core CKAN code.

.. note:: This section deals with the form used to *edit* datasets and groups, not the way they are displayed. For information on customizing the display of forms, see :doc:`theming`. 

.. warning:: This is an advanced topic. Ensure you are familiar with :doc:`extensions` before attempting to customize forms. 

Building a Dataset Form
-----------------------

The Best Way: Extensions
^^^^^^^^^^^^^^^^^^^^^^^^

The best way to build a dataset form is by using a CKAN extension. 

You will firstly need to make a new controller in your extension.  This should subclass PackageController as follows::

 from ckan.controllers.package import PackageController
 class PackageNew(PackageController):
     package_form = 'custom_package_form.html'

The ``package_form`` variable in the subclass will be used as the new form template.

It is recommended that you copy the dataset form (``new_package_form.html``) and make modifications to it. However, it is possible to start from scratch.

To point at this new controller correctly, your extension should look like the following::

 class CustomForm(SingletonPlugin):
     implements(IRoutes)
     implements(IConfigurer)
     def before_map(self, map):
         map.connect('/dataset/new', controller='ckanext.extension_name.controllers.PackageNewController:PackageNew', action='new')
         map.connect('/dataset/edit/{id}', controller='ckanext.extension_name.controllers.PackageNewController:PackageNew', action='edit')
         return map
     def after_map(self, map):
         return map 
     def update_config(self, config):
         configure_template_directory(config, 'templates')

Replace ``extension_name`` with the name of your extension. 

This also assumes that ``custom_package_form.html`` is located in the ``templates`` subdirectory of your extension i.e ``ckanext/extension_name/templates/custom_package_form.html``.

Advanced Use
^^^^^^^^^^^^

The PackageController has more hooks to customize the displayed data. These functions can be overridden in a subclass of PackageController::

  _setup_template_variables(self, context)

This is for setting up new variables for your templates::

  _form_to_db_schema(self)

This defines a navl schema to customize validation and conversion to the database::

  _db_to_form_schema(self)

This defines a navl schema to customize conversion from the database to the form.

A complex example of the use of these hooks can be found in the ``ckanext-dgu`` extension.
