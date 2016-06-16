#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ckan import plugins


def index(package):
    for plugin in plugins.PluginImplementations(plugins.IIndexer):
        return plugin.index(package)


def query(search_query, facets=None, limit=1000, sort=None):
    for plugin in plugins.PluginImplementations(plugins.IIndexer):
        return plugin.query(
            search_query,
            facets=facets,
            limit=limit,
            sort=sort
        )


def reindex(cursor):
    for plugin in plugins.PluginImplementations(plugins.IIndexer):
        return plugin.reindex(cursor)
