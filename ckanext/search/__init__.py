#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ckan import plugins


class NoIndexer(plugins.SingletonPlugin):
    """
    A search indexer that simply does nothing. Documents will not be indexed
    and search results will always return nothing.
    """
    plugins.implements(plugins.IIndexer)

    def index(self, package):
        return True

    def query(self, *args, **kwargs):
        return {
            'results': [],
            'count': 0,
            'search_facets': {},
            'facets': {},
            'sort': 'score'
        }

    def reindex(self, cursor):
        return

    def remove(self, package):
        return


class PostgresIndexer(plugins.SingletonPlugin):
    """
    A search indexer that utilizes PostgreSQL FTS.
    """
    plugins.implements(plugins.IIndexer)

    def index(self, package):
        pass

    def query(self, search_query, facets=None):
        return {'results': [], 'count': 0}

    def reindex(self, cursor):
        return

    def remove(self, package):
        return
