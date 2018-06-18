========================
Testing coding standards
========================

**All new code, or changes to existing code, should have new or updated tests
before being merged into master**. This document gives some guidelines for
developers who are writing tests or reviewing code for CKAN.

.. seealso::

   :doc:`Testing CKAN <test>`
     How to set up your development environment to run CKAN's test suite

   :ref:`background jobs testing`
     How to handle asynchronous background jobs in your tests


--------------------------------------
Transitioning from legacy to new tests
--------------------------------------

CKAN is an old code base with a large legacy test suite in
:mod:`ckan.tests.legacy`. The legacy tests are difficult to maintain and
extend, but are too many to be replaced all at once in a single effort.  So
we're following this strategy:

#. A new test suite has been started in :mod:`ckan.tests`.
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
of code" at a time, and eventually we can delete the legacy :mod:`ckan.tests`
directory entirely.


--------------------------------------
Guidelines for writing new-style tests
--------------------------------------

We want the tests in :mod:`ckan.tests` to be:

Fast
  * Don't share setup code between tests (e.g. in test class ``setup()`` or
    ``setup_class()`` methods, saved against the ``self`` attribute of test
    classes, or in test helper modules).

    Instead write helper functions that create test objects and return them,
    and have each test method call just the helpers it needs to do the setup
    that it needs.

  * Where appropriate, use the ``mock`` library to avoid pulling in other parts
    of CKAN (especially the database), see :ref:`mock`.

Independent
  * Each test module, class and method should be able to be run on its own.

  * Tests shouldn't be tightly coupled to each other, changing a test shouldn't
    affect other tests.

Clear
  It should be quick and easy to see what went wrong when a test fails, or
  to see what a test does and how it works if you have to debug or update
  a test. If you think the test or helper method isn't clear by itself, add
  docstrings.

  You shouldn't have to figure out what a complex test method does, or go and
  look up a lot of code in other files to understand a test method.

  * Tests should follow the canonical form for a unit test, see
    :ref:`test recipe`.

  * Write lots of small, simple test methods not a few big, complex tests.

  * Each test method should test just One Thing.

  * The name of a test method should clearly explain the intent of the test.
    See :ref:`naming`.

Easy to find
  It should be easy to know where to add new tests for some new or changed
  code, or to find the existing tests for some code.

  * See :ref:`organization`

  * See :ref:`naming`.

Easy to write
  Writing lots of small, clear and simple tests that all follow similar
  recipes and organization should make tests easy to write, as well as easy
  to read.

The follow sections give some more specific guidelines and tips for writing
CKAN tests.


.. _organization:

How should tests be organized?
==============================

The organization of test modules in :mod:`ckan.tests` mirrors the
organization of the source modules in :mod:`ckan`::

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


.. _naming:

Naming test methods
-------------------

`The name of a test method should clearly explain the intent of the test <http://docs.pylonsproject.org/en/latest/community/testing.html#rule-name-tcms-to-indicate-what-they-test>`_.

Test method names are printed out when tests fail, so the user can often
see what went wrong without having to look into the test file. When they
do need to look into the file to debug or update a test, the test name
helps to clarify the test.

Do this even if it means your method name gets really long, since we don't
write code that calls our test methods there's no advantage to having short
test method names.

Some modules in CKAN contain large numbers of loosely related functions.
For example, :mod:`ckan.logic.action.update` contains all functions for
updating things in CKAN. This means that
:mod:`ckan.tests.logic.action.test_update` is going to contain an even larger
number of test functions.

So as well as the name of each test method explaining the intent of the test,
tests should be grouped by a test class that aggregates tests against a model
entity or action type, for instance::

    class TestPackageCreate(object):
        # ...
        def test_it_validates_name(self):
            # ...

        def test_it_validates_url(self):
            # ...


    class TestResourceCreate(object)
        # ...
        def test_it_validates_package_id(self):
            # ...

    # ...


Good test names:

* ``TestUserUpdate.test_update_with_id_that_does_not_exist``
* ``TestUserUpdate.test_update_with_no_id``
* ``TestUserUpdate.test_update_with_invalid_name``

Bad test names:

* ``test_user_update``
* ``test_update_pkg_1``
* ``test_package``

.. _test recipe:

Recipe for a test method
========================

The `Pylons Unit Testing Guidelines <http://docs.pylonsproject.org/en/latest/community/testing.html#tips-for-avoiding-bad-unit-tests>`_
give the following recipe for all unit test methods to follow:

1. Set up the preconditions for the method / function being tested.
2. Call the method / function exactly one time, passing in the values
   established in the first step.
3. Make assertions about the return value, and / or any side effects.
4. Do absolutely nothing else.

Most CKAN tests should follow this form. Here's an example of a simple action
function test demonstrating the recipe:

.. literalinclude:: /../ckan/tests/logic/action/test_update.py
   :start-after: # START-AFTER
   :end-before: # END-BEFORE

One common exception is when you want to use a ``for`` loop to call the
function being tested multiple times, passing it lots of different arguments
that should all produce the same return value and/or side effects. For example,
this test from :py:mod:`ckan.tests.logic.action.test_update`:

.. literalinclude:: /../ckan/tests/logic/action/test_update.py
   :start-after: # START-FOR-LOOP-EXAMPLE
   :end-before: # END-FOR-LOOP-EXAMPLE

The behavior of :py:func:`~ckan.logic.action.update.user_update` is the same
for every invalid value.
We do want to test :py:func:`~ckan.logic.action.update.user_update` with lots
of different invalid names, but we obviously don't want to write a dozen
separate test methods that are all the same apart from the value used for the
invalid user name. We don't really want to define a helper method and a dozen
test methods that call it either. So we use a simple loop. Technically this
test calls the function being tested more than once, but there's only one line
of code that calls it.


How detailed should tests be?
=============================

Generally, what we're trying to do is test the *interfaces* between modules in
a way that supports modularization: if you change the code within a function,
method, class or module, if you don't break any of that code's tests you
should be able to expect that CKAN as a whole will not be broken.

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


.. _factory-boy:

Creating test objects: :py:mod:`ckan.tests.factories`
---------------------------------------------------------

.. automodule:: ckan.tests.factories
   :members:


Test helper functions: :mod:`ckan.tests.helpers`
----------------------------------------------------

.. automodule:: ckan.tests.helpers
   :members:


.. _mock:

Mocking: the ``mock`` library
-----------------------------

We use the `mock library <http://www.voidspace.org.uk/python/mock/>`_ to
replace parts of CKAN with mock objects. This allows a CKAN
function to be tested independently of other parts of CKAN or third-party
libraries that the function uses. This generally makes the test simpler and
faster (especially when :py:mod:`ckan.model` is mocked out so that the tests
don't touch the database). With mock objects we can also make assertions about
what methods the function called on the mock object and with which arguments.

.. note::

   Overuse of mocking is discouraged as it can make tests difficult to
   understand and maintain. Mocking can be useful and make tests both faster
   and simpler when used appropriately. Some rules of thumb:

   * Don't mock out more than one or two objects in a single test method.

   * Don't use mocking in more functional-style tests. For example the action
     function tests in :py:mod:`ckan.tests.logic.action` and the
     frontend tests in :py:mod:`ckan.tests.controllers` are functional
     tests, and probably shouldn't do any mocking.

   * Do use mocking in more unit-style tests. For example the authorization
     function tests in :py:mod:`ckan.tests.logic.auth`, the converter and
     validator tests in :py:mod:`ckan.tests.logic.auth`, and most (all?)
     lib tests in :py:mod:`ckan.tests.lib` are unit tests and should use
     mocking when necessary (often it's possible to unit test a method in
     isolation from other CKAN code without doing any mocking, which is ideal).

     In these kind of tests we can often mock one or two objects in a simple
     and easy to understand way, and make the test both simpler and faster.


A mock object is a special object that allows user code to access any attribute
name or call any method name (and pass any parameters) on the object, and the
code will always get another mock object back:

.. code-block:: python

    >>> import mock
    >>> my_mock = mock.MagicMock()
    >>> my_mock.foo
    <MagicMock name='mock.foo' id='56032400'>
    >>> my_mock.bar
    <MagicMock name='mock.bar' id='54093968'>
    >>> my_mock.foobar()
    <MagicMock name='mock.foobar()' id='54115664'>
    >>> my_mock.foobar(1, 2, 'barfoo')
    <MagicMock name='mock.foobar()' id='54115664'>

When a test needs a mock object to actually have some behavior besides always
returning other mock objects, it can set the value of a certain attribute on
the mock object, set the return value of a certain method, specify that a
certain method should raise a certain exception, etc.

You should read the mock library's documentation to really understand what's
going on, but here's an example of a test from
:py:mod:`ckan.tests.logic.auth.test_update` that tests the
:py:func:`~ckan.logic.auth.update.user_update` authorization function and mocks
out :py:mod:`ckan.model`:

.. literalinclude:: /../ckan/tests/logic/auth/test_update.py
   :start-after: # START-AFTER
   :end-before: # END-BEFORE

----

The following sections will give specific guidelines and examples for writing
tests for each module in CKAN.

.. note::

   When we say that *all* functions should have tests in the sections below, we
   mean all *public* functions that the module or class exports for use by
   other modules or classes in CKAN or by extensions or templates.

   *Private* helper methods (with names beginning with ``_``) never have to
   have their own tests, although they can have tests if helpful.

Writing :mod:`ckan.logic.action` tests
--------------------------------------

.. automodule:: ckan.tests.logic.action


Writing :mod:`ckan.logic.auth` tests
------------------------------------

.. automodule:: ckan.tests.logic.auth


Writing converter and validator tests
-------------------------------------

**All converter and validator functions should have unit tests.**

Although these converter and validator functions are tested indirectly by the
action function tests, this may not catch all the converters and validators and
all their options, and converters and validators are not only used by the
action functions but are also available to plugins. Having unit tests will also
help to clarify the intended behavior of each converter and validator.

CKAN's action functions call
:py:func:`ckan.lib.navl.dictization_functions.validate` to validate data posted
by the user. Each action function passes a schema from
:py:mod:`ckan.logic.schema` to
:py:func:`~ckan.lib.navl.dictization_functions.validate`. The schema gives
:py:func:`~ckan.lib.navl.dictization_functions.validate` lists of validation
and conversion functions to apply to the user data. These validation and
conversion functions are defined in :py:mod:`ckan.logic.validators`,
:py:mod:`ckan.logic.converters` and :py:mod:`ckan.lib.navl.validators`.

Most validator and converter tests should be unit tests that test the validator
or converter function in isolation, without bringing in other parts of CKAN or
touching the database.  This requires using the ``mock`` library to mock
``ckan.model``, see :ref:`mock`.

When testing validators, we often want to make the same assertions in many
tests: assert that the validator didn't modify the ``data`` dict, assert that
the validator didn't modify the ``errors`` dict, assert that the validator
raised ``Invalid``, etc. Decorator functions are defined at the top of
validator test modules like :py:mod:`ckan.tests.logic.test_validators` to
make these common asserts easy. To use one of these decorators you have to:

1. Define a nested function inside your test method, that simply calls the
   validator function that you're trying to test.
2. Apply the decorators that you want to this nested function.
3. Call the nested function.

Here's an example of a simple validator test that uses this technique:

.. literalinclude:: /../ckan/tests/logic/test_validators.py
   :start-after: # START-AFTER
   :end-before: # END-BEFORE


No tests for :mod:`ckan.logic.schema.py`
----------------------------------------

.. automodule:: ckan.tests.logic.test_schema


Writing :mod:`ckan.controllers` tests
-------------------------------------

.. automodule:: ckan.tests.controllers


Writing :mod:`ckan.model` tests
-------------------------------

.. automodule:: ckan.tests.model


Writing :mod:`ckan.lib` tests
-----------------------------

.. automodule:: ckan.tests.lib


Writing :mod:`ckan.plugins` tests
---------------------------------

.. automodule:: ckan.tests.plugins


Writing :mod:`ckan.migration` tests
-----------------------------------

.. automodule:: ckan.tests.migration


Writing :mod:`ckan.ckanext` tests
---------------------------------

Within extensions, follow the same guidelines as for CKAN core. For example if
an extension adds an action function then the action function should have
tests, etc.
