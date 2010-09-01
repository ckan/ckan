Example of Usage
----------------

Let's say you're using ckan.net and want a list of all the packages. If you GET
`<http://ckan.net/api/rest/package>`_ then it will return the list of the package
names in JSON format::

["2000-us-census-rdf", "32000-naples-florida-businesses-kml", "aaoe-87", "acawiki", "adb-sdbs", "addgene", "advances-in-dental-research", ... ]

There are several ways you might access this URL:

* simply put this URL into your web browser and save the resulting text file

* you could use a command-line program such as `curl` or `wget`

* you could write a program that uses an http library

* use the Python library `CKAN Client <http://pypi.python.org/pypi/ckanclient>`_

* use command-line tool `Datapkg <http://knowledgeforge.net/ckan/doc/datapkg/>`_. It manages datasets in a similar way as getting software packages with `apt-get` or `CPAN`.

You could search for packages to do with 'open street map' like this: `<http://ckan.net/api/search/package?q=open+street+map>`_ returning::

{"count": 4, "results": ["uk-naptan-osm", "osm-uk", "osm", "naptan"]}

You can see the full record for the `osm` package in JSON format with this: `<http://ckan.net/api/rest/package/osm>`_ which returns::

{"id": "a3dd8f64-9078-4f04-845c-e3f047125028", "name": "osm", "title": "Open Street Map", "version": null, "url": "http://www.openstreetmap.org/", ... }

You might add a tag by a PUT to ``http://ckan.net/api/rest/package/osm`` with this data::

{"tags": ["navigation", "openstreetmap", "map", "geo", "geodata", "xml", "publicdomain", "osm", "my-new-tag"]}

Here we use `curl` to create a new package::

$ curl http://test.ckan.net/api/rest/package -d '{"name":"test", "title":"Test package"}' -H "Authorization: 474d34e4-b710-4b77-b89f-2e909c336b91"

And we create an example package with some government data::

$ curl http://test.ckan.net/api/rest/package -d '{"name": "abstract_of_scottish_agricultural_statistics", "title": "Abstract of Scottish Agricultural Statistics", "version": null, "url": null, "author": "Scottish Government", "author_email": null, "maintainer": null, "maintainer_email": null, "notes": "A long term series of all the main agriculture census items collected in the June census.\n\nSource agency: Scottish Government\n\nDesignation: National Statistics\n\nLanguage: English\n\nAlternative title: Abstract of Scottish Agricultural Statistics", "license_id": "ukcrown-withrights", "tags": ["farm-outputs", "environment", "agriculture", "farming", "agriculture-and-environment"], "extras": {"geographic_coverage": "010000: Scotland", "geographical_granularity": "Country", "external_reference": "ONSHUB", "temporal_granularity": "", "date_updated": "", "agency": "", "precision": "", "temporal_coverage_to": "", "temporal_coverage_from": "", "national_statistic": "yes", "import_source": "ONS-ons_data_50_days_to_2010-05-04", "department": "Scottish Government", "update_frequency": "", "date_released": "2010-03-17", "categories": "Agriculture and Environment"}, "resources": [{"url": "http://www.scotland.gov.uk/Topics/Statistics/Browse/Agriculture-Fisheries", "description": "1982-2008 | hub/id/119-33192", "format": ""}, {"url": "http://www.scotland.gov.uk/Topics/Statistics/Browse/Agriculture-Fisheries", "description": "1982-2007 | hub/id/119-34917", "format": ""}, {"url": "http://www.scotland.gov.uk/Topics/Statistics/Browse/Agriculture-Fisheries", "description": "1983-2009 | hub/id/119-44310", "format": ""}]}' -H "Authorization: d6c3349a-6ccf-45ef-88d4-a8e59a574bf2"



