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
   :end-before: @pytest.mark.ckan_config('ckan.plugins', 'example_iauthfunctions_v3')

To run these extension tests, ``cd`` into the ``ckanext-iauthfunctions``
directory and run this command::

    pytest --ckan-ini=test.ini ckanext/iauthfunctions/tests

Some notes on how these tests work:

* Pytest has lots of useful functions for testing, see the
  `pytest documentation <https://docs.pytest.org/en/latest/>`_.

* We're calling :func:`ckan.tests.call_action` This is a convenience function
  that CKAN provides for its own tests.

* The CKAN core :doc:`/contributing/testing` can usefully be applied to writing tests for plugins.

* CKAN core provides:

  * :mod:`ckan.tests.factories` for creating test data

  * :mod:`ckan.tests.helpers` a collection of helper functions for use in tests

  * :mod:`ckan.tests.pytest_ckan.fixtures` for setting up the test environment

  which are also useful for testing extensions.

* You might also find it useful to read the
  `Flask testing documentation <https://flask-doc.readthedocs.io/en/latest/testing.html>`_ (or
  `Pylons testing documentation <https://docs.pylonsproject.org/projects/pylons-webframework/en/latest/testing.html>`_
  for plugins using legacy pylons controllers).

* Avoid importing the plugin modules directly into your test modules
  (e.g from example_iauthfunctions import plugin_v5_custom_config_setting).
  This causes the plugin to be registered and loaded before the entire test run,
  so the plugin will be loaded for all tests. This can cause conflicts and
  test failures.

.. _test client:

Using the test client
---------------------

It is possible to make requests to the CKAN application from within your tests in order to test the actual responses returned by CKAN. To do so you need to import the ``app`` fixture::

  def test_some_ckan_page(app):

    pass

The ``app`` fixture extends `Flask's Test client <https://flask.palletsprojects.com/en/2.2.x/testing/#sending-requests-with-the-test-client>`_, and can be used to perform GET and POST requests. A Werkzeug's ``TestResponse`` object (`reference <https://werkzeug.palletsprojects.com/en/2.2.x/test/#werkzeug.test.TestResponse>`_) will be returned::

  from ckan.plugins.toolkit import url_for

  def test_dataset_new_page(app):

    url = url_for("group.index")
    response = app.get(url)

    assert "Search groups" in response.body

By default, requests are not authenticated. If you want to make the request impersonating a user in particular, you can pass :ref:`an API Token <api authentication>` in the ``headers`` parameter::

  from ckan.plugins.toolkit import url_for

  def test_group_new_page(app):

      user = factories.UserWithToken()

      url = url_for("group.new")
      response = app.get(
        url,
        headers={"Authorization": user["token"]}
      )

      assert "Create a Group" in response.body

  def test_submit_group_form_page(app):

      user = factories.UserWithToken()

      url = url_for("group.new")
      data = {
        "name": "test-group",
        "title": "Test Group",
        "description": "Some test group",
        "save": ""
      }
      response = app.post(
        url,
        headers={"Authorization": user["token"]},
        data=data,
      )

      assert data["title"] in response.body
      assert call_action("group_show", id=data["name"])



.. todo::

   Link to CKAN guidelines for *how* to write tests, once those guidelines have
   been written. Also add any more extension-specific testing details here.
