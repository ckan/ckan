Testing extensions
==================

CKAN extensions can have their own tests that are run using ``pytest``
in much the same way as running CKAN's own tests (see :doc:`/contributing/test`).

Continuing with our :doc:`example_iauthfunctions extension <tutorial>`,
first we need a CKAN config file to be used when running our tests.
Create the file ``ckanext-iauthfunctions/test.ini`` with the following
contents::

    [app:main]
    use = config:../ckan/test-core.ini

The ``use`` line declares that this config file inherits the settings from the
config file used to run CKAN's own tests (``../ckan`` should be the path to
your CKAN source directory, relative to your ``test.ini`` file).

The ``test.ini`` file is a CKAN config file just like your |ckan.ini|
file, and it can contain any
:doc:`CKAN config file settings </maintaining/configuration>` that you want
CKAN to use when running your tests, for example::

    [app:main]
    use = config:../ckan/test-core.ini
    ckan.site_title = My Test CKAN Site
    ckan.site_description = A test site for testing my CKAN extension

Next, make the directory that will contain our test modules::

    mkdir ckanext-iauthfunctions/ckanext/iauthfunctions/tests/

Finally, create the file
``ckanext-iauthfunctions/ckanext/iauthfunctions/tests/test_iauthfunctions.py``
with the following contents:

.. literalinclude:: ../../ckanext/example_iauthfunctions/tests/test_example_iauthfunctions.py
   :end-before: class TestExampleIAuthFunctionsPluginV3

To run these extension tests, ``cd`` into the ``ckanext-iauthfunctions``
directory and run this command::

    pytest --ckan-ini=test.ini ckanext/iauthfunctions/tests

Some notes on how these tests work:

* Pytest has lots of useful functions for testing, see the
  `pytest documentation <https://docs.pytest.org/en/latest/>`_.

* We're calling :func:`ckan.tests.call_action_api` to post (simulated) HTTP
  requests to the CKAN API. This is a convenience function that CKAN provides
  for its own tests.

* You might also find it useful to read the
  `Pylons testing documentation <http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/testing.html>`_.

* The Pylons book also has a `chapter on testing <http://pylonsbook.com/en/1.0/testing.html>`_.

* Avoid importing the plugin modules directly into your test modules
  (e.g from example_iauthfunctions import plugin_v5_custom_config_setting).
  This causes the plugin to be registered and loaded before the entire test run,
  so the plugin will be loaded for all tests. This can cause conflicts and
  test failures.

.. todo::

   Link to CKAN guidelines for *how* to write tests, once those guidelines have
   been written. Also add any more extension-specific testing details here.
