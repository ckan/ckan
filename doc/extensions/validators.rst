Validator functions reference
=============================

Validators in CKAN are user-defined functions that serves two purposes:

* ensure that input satisfies requirements
* convert the input into expected form

Validators can be defined as a function that accepts one, two or four
arguments. But these implementation details must not bother you, as one must
never call validators directly. Instead,
:py:func:`ckan.plugins.toolkit.navl_validate` function must be used whenever
input requires validation.

.. code-block::

   import ckan.plugins.toolkit as tk
   from ckanext.my_ext.validators import is_valid

   data, errors = tk.navl_validate(
       {"input": "value"},
       {"input": [is_valid]},
   )


And in order to make it more flexible, don't import validator
functions. Instead, register them via
:py:class:`~ckan.plugins.interfaces.IValidators` interface and get using
:py:func:`ckan.plugins.tookit.get_validator` function.

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
parameters. In addition it accepts third optional parameter. That's their
purpose:

1. Data that requires validation. Must be represented by `dict` object.
2. Validation schema. It's a mapping of field names to the lists of validators
   for these fields.
3. Optional context. Contains any extra details that can change validation
   workflow in special cases. For the simpliticy sake, we are not going to use
   context in this section.


Let's imagine the input, that contains two fields ``first`` and ``second``. The
``first`` must be an integer and must be provided, while ``second`` is an
optional string. If we have following four validators:

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

If input is valid, ``data`` contains validated input and ``errors`` is an empty
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
