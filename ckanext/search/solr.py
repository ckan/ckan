#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import datetime

import pysolr
from pylons import config
from ckan import plugins


def solr_datetime_decoder(d):
    for k, v in d.items():
        if not isinstance(v, basestring):
            continue

        possible_datetime = pysolr.DATETIME_REGEX.search(v)
        if possible_datetime:
            date_values = possible_datetime.groupdict()

            for dk, dv in date_values.iteritems():
                date_values[dk] = int(dv)

            d[k] = datetime.datetime(
                date_values['year'],
                date_values['month'],
                date_values['day'],
                date_values['hour'],
                date_values['minute'],
                date_values['second']
            )

    return d


class SolrIndexer(plugins.SingletonPlugin):
    """
    A search indexer that utilizes Solr.
    """
    plugins.implements(plugins.IIndexer, inherit=True)

    def index(self, package):
        pass

    def query(self, search_query, facets=None, limit=1000, sort=None,
              include_inactive=False):
        solr = self._get_connection()

        # By default we want to return all packages.
        if search_query in (None, ''):
            search_query = '*:*'

        # By default we want to sort by search score, with a secondary sort
        # to order by last-updated.
        if sort is None:
            sort = [('score', 'desc'), ('metadata_modified', 'desc')]

        # LEGACY: Multiple CKAN instances can live on the same Solr core.
        #         Filter the results to only show the current site results.
        fq = ['+site_id:{0}'.format(config.get('ckan.site_id'))]

        if not include_inactive:
            fq.append('+state:active')

        response = solr.search(search_query, **{
            'rows': limit,
            'sort': ', '.join(' '.join(pair) for pair in sort),
            'facet': 'true',
            'fq': fq
        })

        # LEGACY: Take all the top-level extras and move them into an "extras"
        #         dict.
        for result in response.docs:
            result['extras'] = extras = {}

            for k in result.keys():
                if k.startswith('extras_'):
                    extras[k[7:]] = result.pop(k)

        return {
            'results': response.docs,
            'count': response.hits,
            'sort': sort,
            'facets': {},
            'search_facets': {}
        }

    def remove(self, package):
        self._get_connection().delete(
            q='id:{package_id}'.format(
                package.id
            ),
            fq=[
                '+site_id:{0}'.format(config.get('ckan.site_id'))
            ]
        )

    def _get_connection(self):
        return pysolr.Solr(
            config.get('solr_url'),
            # Use a custom decoder that will "fix" datetimes stored in solr.
            decoder=json.JSONDecoder(
                object_hook=solr_datetime_decoder
            )
        )


class SolrCloudIndexer(SolrIndexer):
    """
    An indexer for zookeeper/SolrCloud-backed Solr.

    Two values are expected in your configuration:

        - solr_url = the array of zookeeper domains
        - solr_collection = the name of the solr collection to use
    """
    def _get_connection(self):
        zookeeper = pysolr.Zookeeper(config['solr_url'])
        return pysolr.SolrCloud(zookeeper, config['solr_collection'])
