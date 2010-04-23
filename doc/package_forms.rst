Package Forms
=============

The form used to edit Packages in CKAN can be customised. This makes it easier to help users input data, helping them choose from sensible options or to use different data formats. This document sets out to show how this is achieved, without getting embroilled in the main CKAN code.

Each form is defined in a python script and then 'plugged-in' to the CKAN code.
The form script uses the FormBuilder to simply select from the standard field types, or even define some more field types. You can easily specify the content of drop-downs, hint text and the order of fields which are displayed.

Note that this section deals with the form used to *edit* the package, not the way the package is displayed. Display is done in the CKAN templates.


Location of related code
------------------------

In the CKAN code, the majority of forms code is in ckan/forms.

 * ckan/forms/common.py - A common place for fields used by standard forms
 * ckan/forms/builder.py - The FormBuilder class, which provides an easy way to define a form. It creates a FormAlchemy fieldset used in the CKAN controller code.
 * ckan/forms/package.py - This contains the 'standard' form, which is a good example and is useful to derive custom forms from.
 * ckan/forms/package_gov.py - Contains the a government form, which serves as an example of using lots of extra fields for dates, geographical coverage, etc.


Building a package form
-----------------------

Basics
^^^^^^

The *PackageFormBuilder* class initialises with the basic package form which we can then configure:: 

 builder = PackageFormBuilder()

All the basic package fields are added to the form automatically - this currently includes: name, title, version, url, author, author_email, maintainer, maintainer_email, notes and license_id. In case this changes in future, consult the fields for table 'Package' in ckan/model/core.py.

To provide editing of other fields beyond the basic ones, you need to use *add_field* and select either an existing *ConfiguredField* in common.py, or define your own. For example, the autocompleting tag entry field is defined as a field in common.py and it is added to the standard form like this::

 builder.add_field(common.TagField('tags'))

The basic fields (name, title, etc) and a few more (license, tags, resources) are defined for all packages. Additional information can be stored on each package in the 'extra' fields. Often we want to provide a nicer interface to these 'extra' fields to help keep consistency in format between the packages. For example, in the government form (package_gov.py) we have added a field for the release date. This is stored as a Package 'extra' with key 'date_released' and by using the DateExtraField, in the form the user is asked for a date.::

 builder.add_field(common.DateExtraField('date_released'))

You can configure existing fields using the usual `FormAlchemy Field options <http://docs.formalchemy.org/fields.html#fields>`_. For example, here we add a validator to a standard field::

 builder.set_field_option('name', 'validate', package_name_validator)

Options are given keyword parameters by passing a dictionary. For example, this is how we set the notes field's size::

 builder.set_field_option('notes', 'textarea', {'size':'60x15'})

Fields in package forms are grouped together. You should specify which fields are displayed in which groups and in which order like this::

 from sqlalchemy.util import OrderedDict
 builder.set_displayed_fields_in_groups(OrderedDict([
        ('Basic information', ['name', 'title', 'version', 'url']),
        ('Resources', ['resources']),
        ('Detail', ['author', 'author_email'])]))

To complete the form design you need to return the fieldset object. Ensure this is executed once - when your python form file is imported:: 

 my_fieldset = builder.get_fieldset()


Field labels
^^^^^^^^^^^^

The field labels are derived from the model key using a 'prettify' function. The default munge capitalises the first letter and changes underscores to spaces. You can write a more advanced function depending on your needs. Here is the template for a prettify function::

 def prettify(field_name):
     return field_name.replace('_', ' ').capitalize())

If you write a new one, you tell the builder about it like this::

 builder.set_label_prettifier(prettify)


Templates
^^^^^^^^^

Package forms by default use the Genshi template *ckan/package/form.html*. If you want to use a modified one then specify it for example like this::

 builder.set_form_template('package/my_form')


Hidden labels
^^^^^^^^^^^^^

A couple of common fields (ResourceField and ExtrasField currently) are designed to go in their own field group (see below) and without the usual field label. To hide the label, add these fields like this::

 builder.add_field(common.ResourcesField('resources', hidden_label=True))

Instead of starting with just the basic fields, many people will want to edit the standard form, which already contains the resources, extra fields and customise that further. To achieve that you import the builder object like this::

 import ckan.forms.package as package
 builder = package.build_package_form()


Defining custom fields
----------------------

If you want to define a completely new field then here is a useful template::

 class MyField(common.ConfiguredField):
     def get_configured(self):
         return self.MyField(self.name).with_renderer(self.MyRenderer).validate(self.my_validator)

     class MyField(formalchemy.Field):
         def sync(self):
             # edit self.model with using value self._deserialize()

     class MyRenderer(formalchemy.fields.FieldRenderer):
         def render(self, **kwargs):
             # return html of field editor based on self._value

         def _serialized_value(self):
             # take self._params and serialize them ready for rendering
             # or self.deserialize() into python value that can be saved
             # on a sync.

     def my_validator(self, val, field):
        if not ...:
            raise formalchemy.ValidationError('Invalid value')            
        
More examples are in common.py and further information can be obtained from the `FormAlchemy documentation <http://docs.formalchemy.org/>`_.


Using a custom form
-------------------

To register your new form with CKAN you need to do three things. 

1. In your form you need a function that returns your new form's field set. 

 For example you might add below your form code::

  my_fieldset = builder.get_fieldset()

  def get_fieldset(is_admin=False):
      return my_fieldset
  
 (The *is_admin* parameter can be considered if you wish to return a different fieldset for administrator users.)

2. You need to provide an 'entry point' into your code package so that CKAN can access your new form. 

 It is anticipated that your form code will live in a python package outside the CKAN main code package, managed by setuptools. The entry points are listed in the python package's setup.py and you just need to add a category [ckan.forms] and list the function that returns::

  from setuptools import setup, find_packages
  setup(
      ...

      entry_points="""
      [ckan.forms]
      my_form = my_module.forms.my_form:get_fieldset
      """,
  )

 For this change to have an effect, you need to recreate the egg information, so run::

 $ python setup.py egg_info

3. Change an option in your CKAN pylons config file to switch to using the new form.

 For example, your pylons config file will probably be 'development.ini' during development, when you 'paster serve' your CKAN app for testing.

 You need to change the 'package_form' setting in the '[app:main]' section to the name defined int he entry point. For example::

  [app:main]
  ...
  package_form = my_form

 For this to have an effect you may need to restart the pylons (either by restarting the 'serve' command or the Apache host). Now go and edit a package and try out the new form!

 You can also override the config file setting with a URL parameter in your browser. For example you might browse:

 http://eco.ckan.net/package/edit/water-voles?package_form=my_form