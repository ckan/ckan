==================
Importing Datasets
==================

You can add datasets using CKAN's web interface, but when importing many
datasets it's usually more efficient to automate the process in some way.
Common approaches to automatically importing datasets into CKAN include:

* :ref:`Importing datasets with the CKAN API <import-data-api>`.
* Importing datasets with the
  `CKAN harvester extension <https://github.com/okfn/ckanext-harvest/>`_.
  The harvester extension provides web and command-line interfaces for managing
  larger import tasks.

.. tip ::

  If loading your data requires scraping a web page regularly, you may find it
  best to write a scraper on `ScraperWiki <http://www.scraperwiki.com>`_ and
  combine this with one of the methods above.

.. _import-data-api:

Importing Datasets with the CKAN API
------------------------------------

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
