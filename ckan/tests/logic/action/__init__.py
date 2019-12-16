# encoding: utf-8
"""**All action functions should have tests.**

Most action function tests will be high-level tests that both test the code in
the action function itself, and also indirectly test the code in
:mod:`ckan.lib`, :mod:`ckan.model`, :mod:`ckan.logic.schema` etc. that the
action function calls. This means that most action function tests should *not*
use mocking.

Tests for action functions should use the
:func:`ckan.tests.helpers.call_action` function to call the action
functions.

One thing :func:`~ckan.tests.helpers.call_action` does is to add
``ignore_auth: True`` into the ``context`` dict that's passed to the action
function, so that CKAN will not call the action function's authorization
function.  The tests for an action function *don't* need to cover
authorization, because the authorization functions have their own tests in
:mod:`ckan.tests.logic.auth`. But action function tests *do* need to cover
validation, more on that later.

Action function tests *should* test the logic of the actions themselves, and
*should* test validation (e.g. that various kinds of valid input work as
expected, and invalid inputs raise the expected exceptions).

Here's an example of a simple :mod:`ckan.logic.action` test:

.. literalinclude:: ../../ckan/tests/logic/action/test_update.py
   :start-after: # START-AFTER
   :end-before: # END-BEFORE

.. todo::

   Insert the names of all tests for ``ckan.logic.action.update.user_update``,
   for example, to show what level of detail things should be tested in.

"""
