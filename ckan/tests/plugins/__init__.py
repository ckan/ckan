# encoding: utf-8

'''The plugin interfaces in :mod:`ckan.plugins.interfaces` are not directly
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

Other than the plugin interfaces and plugins toolkit, any other code in
:mod:`ckan.plugins` should have tests.

'''
