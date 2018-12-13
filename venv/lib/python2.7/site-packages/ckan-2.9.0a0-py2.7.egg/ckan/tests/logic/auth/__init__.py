# encoding: utf-8

'''**All auth functions should have tests.**

Most auth function tests should be unit tests that test the auth function in
isolation, without bringing in other parts of CKAN or touching the database.
This requires using the ``mock`` library to mock ``ckan.model``, see
:ref:`mock`.

Tests for auth functions should use the
:func:`ckan.tests.helpers.call_auth` function to call auth functions.

Here's an example of a simple :py:mod:`ckan.logic.auth` test:

.. literalinclude:: ../../ckan/tests/logic/auth/test_update.py
   :start-after: # START-AFTER
   :end-before: # END-BEFORE

'''
