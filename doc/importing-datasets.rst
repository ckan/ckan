==================
Importing Datasets
==================

You can create individual datasets using the CKAN front-end.
However, when importing multiple datasets it is generally more efficient to
automate this process in some way.
There are two common approaches to importing datasets in CKAN:

* :ref:`load-data-api`. Using the `CKAN API <api.html>`_.

* :ref:`load-data-harvester`. Using the
  `CKAN harvester extension <https://github.com/okfn/ckanext-harvest/>`_.
  This provides web and command-line interfaces for larger import tasks.

.. note :: If loading your data requires scraping a web page regularly, you
  may find it best to write a scraper on
  `ScraperWiki <http://www.scraperwiki.com>`_ and combine this with either of
  the methods above.


.. _load-data-api:

Import Data with the CKAN API
-----------------------------

You can use the `CKAN API <api.html>`_ to upload datasets directly into your
CKAN instance. Here's an example script that creates a new dataset::

    #!/usr/bin/env python
    import urllib2
    import urllib
    import json
    import pprint

    # Put the details of the dataset we're going to create into a dict.
    dataset_dict = {
        'name': 'my_dataset_name',
        'notes': 'A long description of my dataset',
    }

    # Use the json module to dump the dictionary to a string for posting.
    data_string = urllib.quote(json.dumps(dataset_dict))

    # We'll use the package_create function to create a new dataset.
    request = urllib2.Request(
        'http://www.my_ckan_site.com/api/action/package_create')

    # Creating a dataset requires an authorization header.
    # Replace *** with your API key, from your user account on the CKAN site
    # that you're creating the dataset on.
    request.add_header('Authorization', '***')

    # Make the HTTP request.
    response = urllib2.urlopen(request, data_string)
    assert response.code == 200

    # Use the json module to load CKAN's response into a dictionary.
    response_dict = json.loads(response.read())
    assert response_dict['success'] is True

    # package_create returns the created package as its result.
    created_package = response_dict['result']
    pprint.pprint(created_package)


.. _load-data-harvester:

Import Data with the Harvester Extension
----------------------------------------

The `CKAN harvester extension <https://github.com/okfn/ckanext-harvest/>`_
provides useful tools for more advanced data imports.

These include a command-line interface and a web user interface for running
harvesting jobs.

To use the harvester extension, create a class that implements the
`harvester interface <https://github.com/okfn/ckanext-harvest/blob/master/ckanext/harvest/interfaces.py>`
derived from the
`base class of the harvester extension <https://github.com/okfn/ckanext-harvest/blob/master/ckanext/harvest/harvesters/base.py>`_.

For more information on working with extensions, see :doc:`extensions`.
