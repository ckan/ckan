# encoding: utf-8

'''
Controller tests probably shouldn't use mocking.

.. todo::

   Write the tests for one controller, figuring out the best way to write
   controller tests. Then fill in this guidelines section, using the first set
   of controller tests as an example.

   Some things have been decided already:

   * All controller methods should have tests

   * Controller tests should be high-level tests that work by posting simulated
     HTTP requests to CKAN URLs and testing the response. So the controller
     tests are also testing CKAN's templates and rendering - these are CKAN's
     front-end tests.

     For example, maybe we use a webtests testapp and then use beautiful soup
     to parse the HTML?

   * In general the tests for a controller shouldn't need to be too detailed,
     because there shouldn't be a lot of complicated logic and code in
     controller classes. The logic should be handled in other places such as
     :mod:`ckan.logic` and :mod:`ckan.lib`, where it can be tested easily and
     also shared with other code.

   * The tests for a controller should:

     * Make sure that the template renders without crashing.

     * Test that the page contents seem basically correct, or test certain
       important elements in the page contents (but don't do too much HTML
       parsing).

     * Test that submitting any forms on the page works without crashing and
       has the expected side-effects.

     * When asserting side-effects after submitting a form, controller tests
       should user the :func:`ckan.tests.helpers.call_action` function. For
       example after creating a new user by submitting the new user form, a
       test could call the :func:`~ckan.logic.action.get.user_show` action
       function to verify that the user was created with the correct values.

.. warning::

   Some CKAN controllers *do* contain a lot of complicated logic code.  These
   controllers should be refactored to move the logic into :mod:`ckan.logic` or
   :mod:`ckan.lib` where it can be tested easily.  Unfortunately in cases like
   this it may be necessary to write a lot of controller tests to get this
   code's behavior into a test harness before it can be safely refactored.

'''
