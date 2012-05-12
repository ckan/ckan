==================
Using the Data API
==================

The following provides an introduction to using the CKAN :doc:`DataStore
<datastore>` Data API.

Introduction
============

Each 'table' in the DataStore is an ElasticSearch_ index type ('table'). As
such the Data API for each CKAN resource is directly equivalent to a single
index 'type' in ElasticSearch (we tend to refer to it as a 'table').

This means you can (usually) directly re-use `ElasticSearch client libraries`_
when connecting to a Data API endpoint. It also means that what follows is, in
essence, a tutorial in using the ElasticSearch_ API.

The following short set of slides provide a brief overview and introduction to
the DataStore and the Data API.

.. raw:: html

   <iframe src="https://docs.google.com/presentation/embed?id=1UhEqvEPoL_VWO5okYiEPfZTLcLYWqtvRRmB1NBsWXY8&#038;start=false&#038;loop=false&#038;delayms=3000" frameborder="0" width="480" height="389" allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>

.. _ElasticSearch: http://elasticsearch.org/
.. _ElasticSearch client libraries: http://www.elasticsearch.org/guide/appendix/clients.html

Quickstart
==========

``{{endpoint}}`` refers to the data API endpoint (or ElasticSearch index /
table). For example, on the DataHub_ this gold prices data resource
http://datahub.io/dataset/gold-prices/resource/b9aae52b-b082-4159-b46f-7bb9c158d013
would have its Data API endpoint at:
http://datahub.io/api/data/b9aae52b-b082-4159-b46f-7bb9c158d013. If you were
just using ElasticSearch standalone an example of an endpoint would be:
http://localhost:9200/gold-prices/monthly-price-table.

.. note::  every resource on a CKAN instance for which a DataStore table is
           enabled provides links to its Data API endpoint via the Data API
           button at the top right of the resource page.

Key urls:

* Query: ``{{endpoint}}/_search`` (in ElasticSearch < 0.19 this will return an
  error if visited without a query parameter)

  * Query example: ``{{endpoint}}/_search?size=5&pretty=true``

* Schema (Mapping): ``{{endpoint}}/_mapping``

.. _DataHub: http://datahub.io/

Examples
--------

cURL (or Browser)
~~~~~~~~~~~~~~~~~

The following examples utilize the cURL_ command line utility. If you prefer,
you you can just open the relevant urls in your browser::

  // query for documents / rows with title field containing 'jones'
  // added pretty=true to get the json results pretty printed
  curl {{endpoint}}/_search?q=title:jones&size=5&pretty=true

Adding some data (requires an :ref:`API Key <get-api-key>`)::

  // requires an API key
  // Data (argument to -d) should be a JSON document
  curl -X POST -H "Authorization: {{YOUR-API-KEY}}" {{endpoint}} -d '{
    "title": "jones",
    "amount": 5.7
  }'

.. _cURL: http://curl.haxx.se/

Javascript
~~~~~~~~~~

A simple ajax (JSONP) request to the data API using jQuery::

  var data = {
    size: 5 // get 5 results
    q: 'title:jones' // query on the title field for 'jones'
  };
  $.ajax({
    url: {{endpoint}}/_search,
    dataType: 'jsonp',
    success: function(data) {
      alert('Total results found: ' + data.hits.total)
    }
  });

The Data API supports CORs so you can also write to it (this requires the json2_ library for ``JSON.stringify``)::

  var data = {
    title: 'jones',
    amount: 5.7
  };
  $.ajax({
    url: {{endpoint}},
    type: 'POST',
    data: JSON.stringify(data),
    success: function(data) {
      alert('Uploaded ok')
    }
  });

.. _json2: https://github.com/douglascrockford/JSON-js/blob/master/json2.js

Python
~~~~~~

.. note:: You can also use the `DataStore Python client library`_.

.. _DataStore Python client library: http://github.com/okfn/datastore-client

::

  import urllib2
  import json

  # =================================
  # Store data in the DataStore table

  url = '{{endpoint}}'
  data = {
      'title': 'jones',
      'amount': 5.7
      }
  # have to send the data as JSON
  data = json.dumps(data)
  # need to add your API key (and have authorization to write to this endpoint)
  headers = {'Authorization': 'YOUR-API-KEY'}

  req = urllib2.Request(url, data, headers)
  out = urllib2.urlopen(req)
  print out.read()

  # =========================
  # Query the DataStore table

  url = '{{endpoint}}/_search?q=title:jones&size=5'
  req = urllib2.Request(url)
  out = urllib2.urlopen(req)
  data = out.read()
  print data
  # returned data is JSON
  data = json.loads(data)
  # total number of results
  print data['hits']['total']

Querying
========

Basic Queries Using Only the Query String
-----------------------------------------

Basic queries can be done using only query string parameters in the URL. For
example, the following searches for text 'hello' in any field in any document
and returns at most 5 results::

  {{endpoint}}/_search?q=hello&size=5

Basic queries like this have the advantage that they only involve accessing a
URL and thus, for example, can be performed just using any web browser.
However, this method is limited and does not give you access to most of the
more powerful query features.

Basic queries use the `q` query string parameter which supports the `Lucene
query parser syntax`_ and hence filters on specific fields (e.g. `fieldname:value`), wildcards (e.g. `abc*`) and more.

.. _Lucene query parser syntax: http://lucene.apache.org/core/old_versioned_docs/versions/3_0_0/queryparsersyntax.html

There are a variety of other options (e.g. size, from etc) that you can also
specify to customize the query and its results. Full details can be found in
the `ElasticSearch URI request docs`_.

.. _ElasticSearch URI request docs: http://www.elasticsearch.org/guide/reference/api/search/uri-request.html

Full Query API
--------------

More powerful and complex queries, including those that involve faceting and
statistical operations, should use the full ElasticSearch query language and API.

In the query language queries are written as a JSON structure and is then sent
to the query endpoint (details of the query langague below). There are two
options for how a query is sent to the search endpoint:

1. Either as the value of a source query parameter e.g.::

    {{endpoint}}/_search?source={Query-as-JSON}

2. Or in the request body, e.g.::

    curl -XGET {{endpoint}}/_search -d 'Query-as-JSON'

   For example::

    curl -XGET {{endpoint}}/_search -d '{
        "query" : {
            "term" : { "user": "kimchy" }
        }
    }'


Query Language
==============

Queries are JSON objects with the following structure (each of the main
sections has more detail below)::

    {
        size: # number of results to return (defaults to 10)
        from: # offset into results (defaults to 0)
        fields: # list of document fields that should be returned - http://elasticsearch.org/guide/reference/api/search/fields.html
        sort: # define sort order - see http://elasticsearch.org/guide/reference/api/search/sort.html

        query: {
            # "query" object following the Query DSL: http://elasticsearch.org/guide/reference/query-dsl/
            # details below
        },

        facets: {
            # facets specifications
            # Facets provide summary information about a particular field or fields in the data
        }

        # special case for situations where you want to apply filter/query to results but *not* to facets
        filter: {
            # filter objects
            # a filter is a simple "filter" (query) on a specific field.
            # Simple means e.g. checking against a specific value or range of values
        },
    }

Query results look like::

    {
        # some info about the query (which shards it used, how long it took etc)
        ...
        # the results
        hits: {
            total: # total number of matching documents
            hits: [
                # list of "hits" returned
                {
                    _id: # id of document
                    score: # the search index score
                    _source: {
                        # document 'source' (i.e. the original JSON document you sent to the index
                    }
                }
            ]
        }
        # facets if these were requested
        facets: {
            ...
        }
    }

Query DSL: Overview
-------------------

Query objects are built up of sub-components. These sub-components are either
basic or compound. Compound sub-components may contains other sub-components
while basic may not. Example::

    {
        "query": {
            # compound component
            "bool": {
                # compound component
                "must": {
                    # basic component
                    "term": {
                        "user": "jones"
                    }
                }
                # compound component
                "must_not": {
                    # basic component
                    "range" : {
                        "age" : {
                            "from" : 10,
                            "to" : 20
                        }
                    } 
                }
            }
        }
    }

In addition, and somewhat confusingly, ElasticSearch distinguishes between
sub-components that are "queries" and those that are "filters". Filters, are
really special kind of queries that are: mostly basic (though boolean
compounding is alllowed); limited to one field or operation and which, as such,
are especially performant.

Examples, of filters are (full list on RHS at the bottom of the query-dsl_ page):

  * term: filter on a value for a field
  * range: filter for a field having a range of values (>=, <= etc)
  * geo_bbox: geo bounding box
  * geo_distance: geo distance

.. _query-dsl: http://elasticsearch.org/guide/reference/query-dsl/

Rather than attempting to set out all the constraints and options of the
query-dsl we now offer a variety of examples.

Examples
--------

Match all / Find Everything
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    {
        "query": {
            "match_all": {}
        }
    }

Classic Search-Box Style Full-Text Query
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This will perform a full-text style query across all fields. The query string
supports the `Lucene query parser syntax`_ and hence filters on specific fields
(e.g. `fieldname:value`), wildcards (e.g. `abc*`) as well as a variety of
options. For full details see the query-string_ documentation.

::

    {
        "query": {
            "query_string": {
                "query": {query string}
            }
        }
    }

.. _query-string: http://elasticsearch.org/guide/reference/query-dsl/query-string-query.html

Filter on One Field
~~~~~~~~~~~~~~~~~~~

::

    {
        "query": {
            "term": {
                {field-name}: {value}
            }
        }
    }

High performance equivalent using filters::

    {
        "query": {
            "constant_score": {
                "filter": {
                    "term": {
                        # note that value should be *lower-cased*
                        {field-name}: {value}
                    }
                }
            }
    }

Find all documents with value in a range
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This can be used both for text ranges (e.g. A to Z), numeric ranges (10-20) and
for dates (ElasticSearch will converts dates to ISO 8601 format so you can
search as 1900-01-01 to 1920-02-03).

::

    {
        "query": {
            "constant_score": {
                "filter": {
                    "range": {
                        {field-name}: {
                            "from": {lower-value}
                            "to": {upper-value}
                        }
                    }
                }
            }
        }
    }

For more details see `range filters`_.

.. _range filters: http://elasticsearch.org/guide/reference/query-dsl/range-filter.html

Full-Text Query plus Filter on a Field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    {
        "query": {
            "query_string": {
                "query": {query string}
            },
            "term": {
                {field}: {value}
            }
        }
    }


Filter on two fields
~~~~~~~~~~~~~~~~~~~~

Note that you cannot, unfortunately, have a simple and query by adding two
filters inside the query element. Instead you need an 'and' clause in a filter
(which in turn requires nesting in 'filtered'). You could also achieve the same
result here using a `bool query`_.

.. _bool query: http://elasticsearch.org/guide/reference/query-dsl/bool-query.html

::

    {
        "query": {
            "filtered": {
                "query": {
                    "match_all": {}
                },
                "filter": {
                    "and": [
                        {
                            "range" : {
                                "b" : { 
                                    "from" : 4, 
                                    "to" : "8"
                                }
                            },
                        },
                        {
                            "term": {
                                "a": "john"
                            }
                        }
                    ]
                }
            }
        }
    }

Geospatial Query to find results near a given point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This uses the `Geo Distance filter`_. It requires that indexed documents have a field of `geo point type`_.

.. _Geo Distance filter: http://www.elasticsearch.org/guide/reference/query-dsl/geo-distance-filter.html
.. _geo point type: http://www.elasticsearch.org/guide/reference/mapping/geo-point-type.html

Source data (a point in San Francisco!)::

  # This should be in lat,lon order
  {
    ...
    "Location": "37.7809035011582, -122.412119695795"
  }
  
There are alternative formats to provide lon/lat locations e.g. (see ElasticSearch documentation for more)::

  # Note this must have lon,lat order (opposite of previous example!)
  {
    "Location":[-122.414753390488, 37.7762147914147]
  }

  # or ...
  {
    "Location": {
      "lon": -122.414753390488,
      "lat": 37.7762147914147
    }
  }

We also need a mapping to specify that Location field is of type geo_point as this will not usually get guessed from the data (see below for more on mappings)::

  "properties": {
      "Location": {
          "type": "geo_point"
       }
       ...
  }

Now the actual query::

    {
        "filtered" : {
            "query" : {
                "match_all" : {}
            },
            "filter" : {
                "geo_distance" : {
                    "distance" : "20km",
                    "Location" : {
                        "lat" : 37.776,
                        "lon" : -122.41
                    }
                }
            }
        }
    }    

Note that you can specify the query using specific lat, lon attributes even
though original data did not have this structure (you can also use a query
similar to the original structure if you wish - see `Geo distance filter`_ for
more information).


Facets
------

Facets provide a way to get summary information about then data in an
elasticsearch table, for example counts of distinct values.

ElasticSearch (and hence the Data API) provides rich faceting capabilities:
http://www.elasticsearch.org/guide/reference/api/search/facets/

There are various kinds of facets available, for example (full list on the facets page):

* Terms_ - counts by distinct terms (values) in a field
* Range_ - counts for a given set of ranges in a field
* Histogram_ and `Date Histogram`_ - counts by constant interval ranges
* Statistical_ - statistical summary of a field (mean, sum etc)
* `Terms Stats`_ - statistical summary on one field (stats field) for distinct
  terms in another field. For example, spending stats per department or per
  region.
* `Geo Distance`_: counts by distance ranges from a given point

Note that you can apply multiple facets per query.

.. _Terms: http://www.elasticsearch.org/guide/reference/api/search/facets/terms-facet.html
.. _Range: http://www.elasticsearch.org/guide/reference/api/search/facets/range-facet.html
.. _Histogram: http://www.elasticsearch.org/guide/reference/api/search/facets/histogram-facet.html
.. _Date Histogram: http://www.elasticsearch.org/guide/reference/api/search/facets/date-histogram-facet.html
.. _Statistical: http://www.elasticsearch.org/guide/reference/api/search/facets/statistical-facet.html
.. _Terms Stats: http://www.elasticsearch.org/guide/reference/api/search/facets/terms-stats-facet.html
.. _Geo Distance: http://www.elasticsearch.org/guide/reference/api/search/facets/geo-distance-facet.html


Adding, Updating and Deleting Data
==================================

ElasticSeach, and hence the Data API, have a standard RESTful API. Thus::

  POST      {{endpoint}}         : INSERT
  PUT/POST  {{endpoint}}/{{id}}  : UPDATE (or INSERT)
  DELETE    {{endpoint}}/{{id}}  : DELETE

For more on INSERT and UPDATE see the `Index API`_ documentation.

.. _Index API: http://elasticsearch.org/guide/reference/api/index_.html

There is also support bulk insert and updates via the `Bulk API`_.

.. _Bulk API: http://elasticsearch.org/guide/reference/api/bulk.html

.. note:: The `DataStore Python client library`_ has support for inserting,
          updating (in bulk) and deleting. There is also support for these
          operations in the ReclineJS javascript library.


Schema Mapping
==============

As the ElasticSearch documentation states:

  Mapping is the process of defining how a document should be mapped to the
  Search Engine, including its searchable characteristics such as which fields
  are searchable and if/how they are tokenized. In ElasticSearch, an index may
  store documents of different “mapping types”. ElasticSearch allows one to
  associate multiple mapping definitions for each mapping type.

  Explicit mapping is defined on an index/type level. By default, there isn't a
  need to define an explicit mapping, since one is automatically created and
  registered when a new type or new field is introduced (with no performance
  overhead) and have sensible defaults. Only when the defaults need to be
  overridden must a mapping definition be provided.

Relevant docs: http://elasticsearch.org/guide/reference/mapping/.


JSONP support
=============

JSONP support is available on any request via a simple callback query string parameter::

  ?callback=my_callback_name

