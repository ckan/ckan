Validator functions reference
=============================

Validators in CKAN are user-defined functions that serves two purposes:

* Ensuring that the input satisfies certain requirements
* Converting the input to an expected form

Validators can be defined as a function that accepts one, two or four arguments. But this is an implementation detail 
and validators should not be called directly. Instead, the
:py:func:`ckan.plugins.toolkit.navl_validate` function must be used whenever
input requires validation.

.. code-block::

   import ckan.plugins.toolkit as tk
   from ckanext.my_ext.validators import is_valid

   data, errors = tk.navl_validate(
       {"input": "value"},
       {"input": [is_valid]},
   )


And in order to be more flexible and allow overrides, don't import validator
functions directly. Instead, register them via the
:py:class:`~ckan.plugins.interfaces.IValidators` interface and use the
:py:func:`ckan.plugins.tookit.get_validator` function:

.. code-block::

   import ckan.plugins as p
   import ckan.plugins.toolkit as tk

   def is_valid(value):
       return value

   class MyPlugin(p.SingletonPlugin)
       p.implements(p.IValidators)

       def get_validators(self):
           return {"is_valid": is_valid}

   ...
   # somewhere in code
   data, errors = tk.navl_validate(
       {"input": "value"},
       {"input": [tk.get_validator("is_valid")]},
   )


As you should have already noticed, ``navl_validate`` requires two
parameters and additionally accepts an optional one. That's their
purpose:

1. Data that requires validation. Must be a `dict` object, with keys being the names of the fields.
2. The validation schema. It's a mapping of field names to the lists of validators
   for that particular field.
3. Optional context. Contains any extra details that can change validation
   workflow in special cases. For the simplicity sake, we are not going to use
   context in this section, and in general is best not to rely on context variables 
   inside validators.


Let's imagine an input that contains two fields ``first`` and ``second``. The
``first`` field must be an integer and must be provided, while the ``second`` field 
is an optional string. If we have following four validators:

* ``is_integer``
* ``is_string``
* ``is_required``
* ``is_optional``

we can validate data in the following way::

  input = {"first": "123"}
  schema = {
      "first": [is_required, is_integer],
      "second": [is_optional, is_string],
  }

  data, errors = tk.navl_validate(input, schema)

If the input is valid, ``data`` contains validated input and ``errors`` is an empty
dictionary. Otherwise, ``errors`` contains all the validation errors for the
provided input.


Built-in validators
~~~~~~~~~~~~~~~~~~~

.. automodule:: ckan.lib.navl.validators
   :members:
   :undoc-members:

.. automodule:: ckan.logic.validators
   :members:
   :undoc-members:

.. automodule:: ckan.logic.converters
   :members:
   :undoc-members:
