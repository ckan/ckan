========================
Testing coding standards
========================


------------------------------------------------
Transitioning from the legacy tests to new tests
------------------------------------------------

CKAN is an old code base with a large legacy test suite in
:mod:`ckan.legacy_tests`. The legacy tests are difficult to maintain and
extend, but are too many to be replaced all at once in a single effort.  So
we're following this strategy:

.. todo:: The legacy tests haven't actually been moved to ``ckan.legacy_tests``
   yet.

#. The legacy test suite has been moved to :mod:`ckan.legacy_tests`.
#. The new test suite has been started in :mod:`ckan.tests`.
#. For now, we'll run both the legacy tests and the new tests before
   merging something into the master branch.
#. Whenever we add new code, or change existing code, we'll add new-style tests
   for it.
#. If you change the behavior of some code and break some legacy tests,
   consider adding new tests for that code and deleting the legacy tests,
   rather than updating the legacy tests.
#. Now and then, we'll write a set of new tests to cover part of the code,
   and delete the relevant legacy tests. For example if you want to refactor
   some code that doesn't have good tests, write a set of new-style tests for
   it first, refactor, then delete the relevant legacy tests.

In this way we can incrementally extend the new tests to cover CKAN one "island
of code" at a time, and eventually we can delete the :mod:`legacy_tests`
directory entirely.


--------------------------------------
Guidelines for writing new-style tests
--------------------------------------

.. important::

   All new code, or changes to existing code, should have new or updated tests
   before getting merged into master.

.. todo::

   Maybe give a short list of what we want from the new-style tests at the top
   here.

This section gives guidelines and examples to follow when writing or reviewing
new-style tests. The subsections below cover:

#. `What should be tested?`_ Which parts of CKAN code should have tests,
   and which don't have to?
#. `How should tests be organized?`_ When adding tests for some code, or
   looking for the tests for some code, how do you know where the tests should
   be?
#. `How detailed should tests be?`_ When writing the tests for a function or
   method, how many tests should you write and what should the tests cover?
#. `How should tests be written?`_ What's the formula and guidelines for
   writing a *good* test?


What should be tested?
======================

.. note::

   When we say that *all* functions/methods of a module/class should have
   tests, we mean all *public* functions/methods that the module/class exports
   for use by other modules/classes in CKAN or by extensions or templates.

   *Private* helper methods (with names beginning with ``_``) never have to
   have their own tests, although they can have tests if helpful.

:mod:`ckan.logic.action`
  All action functions should have tests. Note that the tests for an action
  function *don't* need to cover authorization, because the authorization
  functions have their own tests. But action function tests *do* need to cover
  validation, more on that later.

:mod:`ckan.logic.auth`
  All auth functions should have tests.

:mod:`ckan.logic.converters`, :mod:`ckan.logic.validators`
  All converter and validator functions should have unit tests.
  Although these functions are tested indirectly by the action function
  tests, this may not catch all the converters and validators and all their
  options, and converters and validators are not only used by the action
  functions but are also available to plugins. Having unit tests will also
  help to clarify the intended behavior of each converter and validator.

:mod:`ckan.logic.schema.py`
  We *don't* write tests for each schema. The validation done by the schemas
  is instead tested indirectly by the action function tests. The reason for
  this is that CKAN actually does validation in multiple places: some
  validation is done using schemas, some validation is done in the action
  functions themselves, some is done in dictization, and some in the model.
  By testing all the different valid and invalid inputs at the action function
  level, we catch it all in one place.

:mod:`ckan.controllers`
  All controller methods should have tests.

:mod:`ckan.model` and :mod:`ckan.lib`
  All "non-trivial" model and lib functions and methods should have tests.

  .. todo:: Define "trivial" with an example.

  Some code is used by extensions or templates, for example the template
  helpers in :mod:`ckan.lib.helpers`. If a function or method is available to
  extensions or templates then it should have tests, even if you think
  it's trivial.

:mod:`ckan.plugins`
  The plugin interfaces in :mod:`ckan.plugins.interfaces` are not directly
  testable because they don't contain any code, *but*:

  * Each plugin interface should have an example plugin in :mod:`ckan.ckanext`
    and the example plugin should have its own functional tests.

  * The tests for the code that calls the plugin interface methods should test
    that the methods are called correctly.

    For example :func:`ckan.logic.action.get.package_show` calls
    :meth:`ckan.plugins.interfaces.IDatasetForm.read`, so the
    :func:`~ckan.logic.action.get.package_show` tests should include tests
    that :meth:`~ckan.plugins.interfaces.IDatasetForm.read` is called at the
    right times and with the right parameters.

    Everything in :mod:`ckan.plugins.toolkit` should have tests, because these
    functions are part of the API for extensions to use. But
    :mod:`~ckan.plugins.toolkit` imports most of these functions from elsewhere
    in CKAN, so the tests should be elsewhere also, in the test modules for the
    modules where the functions are defined.

:mod:`ckan.migration`
  All migration scripts should have tests.

:mod:`ckan.ckanext`
  Within extensions, follow the same guidelines as for CKAN core. For example
  if an extension adds an action function then the action function should have
  tests, etc.


How should tests be organized?
==============================

The organization of test modules in :mod:`ckan.tests` mirrors the organization
of the source modules in :mod:`ckan`::

  ckan/
    tests/
      controllers/
        test_package.py <-- Tests for ckan/controllers/package.py
        ...
      lib/
        test_helpers.py <-- Tests for ckan/lib/helpers.py
        ...
      logic/
        action/
          test_get.py
          ...
        auth/
          test_get.py
          ...
        test_converters.py
        test_validators.py
      migration/
        versions/
          test_001_add_existing_tables.py
          ...
      model/
        test_package.py
        ...
      ...

There are a few exceptional test modules that don't fit into this structure,
for example PEP8 tests and coding standards tests. These modules can just go in
the top-level ``ckan/tests/`` directory. There shouldn't be too many of these.


How detailed should tests be?
=============================

When you're writing the tests for a function or method, how many tests should
you write and what should the tests cover? Generally, what we're trying to do
is test the *interfaces* between modules in a way that supports modularization:
if you change the code within a function, method, class or module, if you don't
break any of that code's unit tests you should be able to expect that CKAN as a
whole will not be broken.

As a general guideline, the tests for a function or method should:

- Test for success:

  - Test the function with typical, valid input values
  - Test with valid, edge-case inputs
  - If the function has multiple parameters, test them in different
    combinations

- Test for failure:

  - Test that the function fails correctly (e.g. raises the expected type of
    exception) when given likely invalid inputs (for example, if the user
    passes an invalid user_id as a parameter)
  - Test that the function fails correctly when given bizarre input

- Test that the function behaves correctly when given unicode characters as
  input

- Cover the interface of the function: test all the parameters and features of
  the function

.. todo::

   What about sanity tests? For example I should be able to convert a value
   to an extra using convert_to_extras() and then convert it back again using
   convert_from_extras() and get the same value back.

   Private functions and methods that are only used within the module (and
   whose names should begin with underscores) *may* have tests, but don't have
   to.


How should tests be written?
============================

In general, follow the `Pylons Unit Testing Guidelines
<http://docs.pylonsproject.org/en/latest/community/testing.html>`_.
We'll give some additional, CKAN-specific guidelines below:


Naming test methods
-------------------

Some modules in CKAN contain large numbers of more-or-less unrelated functions.
For example, :mod:`ckan.logic.action.update` contains all functions for
updating things in CKAN. This means that
:mod:`ckan.tests.logic.action.test_update` is going to contain an even larger
number of test functions.

So in addition to the name of each test function clearly explaining the intent
of the test, it's important to name the test function after the function it's
testing, for example all the tests for ``user_update`` should be named
``test_user_update_*``:

* ``test_user_update_name``
* ``test_user_update_password``
* ``test_user_update_with_id_that_does_not_exist``
* etc.

It's also a good idea to keep all the ``user_update`` tests next to each other
in the file, and to order the tests for each function in the same order as the
functions are ordered in the source file.

In smaller modules putting the source function name in the test function names
may not be necessary, but for a lot of modules in CKAN it's probably a good
idea.

:mod:`ckan.tests.helpers` and :mod:`ckan.tests.data`
----------------------------------------------------

.. todo::

   There are some test helper functions here. Explain what they're for and
   maybe autodoc them here.


:mod:`ckan.tests.logic.action`
------------------------------

Tests for action functions should use the
:func:`ckan.tests.helpers.call_action` function to call the action functions.

One thing :func:`~ckan.tests.helpers.call_action` does is to add
``ignore_auth: True`` into the ``context`` dict that's passed to the action
function. This means CKAN will not call the action function's authorization
function. :mod:`ckan.tests.logic.action` should not test authorization
(e.g. testing that users that should not be authorized cannot call an action,
etc.) because the authorization functions are tested separately in
:mod:`ckan.tests.logic.auth`.

Action function tests *should* test the logic of the actions themselves, and
*should* test validation (e.g. that various kinds of valid input work as
expected, and invalid inputs raise the expected exceptions).

.. todo::

   Insert some examples here.


:mod:`ckan.tests.controllers`
-----------------------------

Tests for controller methods should work by simulating HTTP requests and
testing the HTML that they get back.

In general the tests for a controller shouldn't need to be too detailed,
because there shouldn't be a lot of complicated logic and code in controller
classes (the logic should be handled in :mod:`ckan.logic` and :mod:`ckan.lib`,
for example). The tests for a controller should:

* Make sure that the template renders without crashing.

* Test that the page contents seem basically correct, or test certain important
  elements in the page contents (but don't do too much HTML parsing).

* Test that submitting any forms on the page works without crashing and has
  the expected side-effects.

When asserting side-effects after submitting a form, controller tests should
user the :func:`ckan.tests.helpers.call_action` function. For example after
creating a new user by submitting the new user form, a test could call the
:func:`~ckan.logic.action.get.user_show` action function to verify that the
user was created with the correct values.

.. warning::

   Some CKAN controllers *do* contain a lot of complicated logic code.  These
   controllers should be refactored to move the logic into :mod:`ckan.logic` or
   :mod:`ckan.lib` where it can be tested easily.  Unfortunately in cases like
   this it may be necessary to write a lot of controller tests to get this
   code's behavior into a test harness before it can be safely refactored.

.. todo::

   How exactly should controller tests work? (e.g. with a webtest testapp and
   beautifulsoup?)

   Insert examples here.


Mocking
-------

.. todo::

   Some examples of how (and when/where) to use the ``mock`` library in CKAN.
