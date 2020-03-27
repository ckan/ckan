# -*- coding: utf-8 -*-

import re
import logging

from pprint import pformat

import click
import requests

import ckan.lib.search as search
import ckan.plugins as p

log = logging.getLogger(__name__)

field_groups = [
    u"copy-field",
    u"dynamic-field",
    u"field",
    u"field-type",
]


class Solr(object):
    @property
    def url(self):
        url, _, _ = search.SolrSettings.get()
        return url

    @property
    def schema_url(self):
        return self.url.rstrip(u"/") + u"/schema"

    def get_schema(self):
        return requests.get(self.schema_url).json()[u"schema"]

    def clear_schema(self, groups):
        schema = self.get_schema()
        for group in groups:
            key = re.sub(u"-\\w", lambda m: m.group()[1:].title(),
                         group) + u"s"
            if not schema[key]:
                continue
            if group == u"copy-field":
                data = {u"delete-" + group: schema[key]}
            else:
                data = {
                    u"delete-" + group:
                    [dict(name=field[u"name"]) for field in schema[key]]
                }
            resp = self._post(data)
            log.info(u"Solr schema API. Delete %s: %s", group, pformat(resp))

    def create_schema(self, groups):
        self.clear_schema(groups)
        definitions = {key: [] for key in field_groups}
        for plugin in p.PluginImplementations(p.ISearchSchema):
            plugin.update_search_schema_definitions(definitions)

        for group in reversed(groups):
            data = {u"add-" + group: definitions[group]}
            resp = self._post(data)
            log.info(u"Solr schema API. add %s: %s", group, pformat(resp))

    def _post(self, data):

        return requests.post(self.schema_url, json=data).json()


@click.group(u"search-schema")
def search_schema():
    """Manage search schema (Solr's schema.xml).

    """
    pass


@search_schema.command()
def describe():
    """List currently used fields.

    """
    click.echo(pformat(Solr().get_schema()))


@search_schema.command()
@click.argument(u"target", type=click.Choice(field_groups), required=False)
def clear(target):
    """Remove existing field definitions.

    """
    target = [target] if target else field_groups
    Solr().clear_schema(target)
    click.secho(u"Done", fg=u"green")


@search_schema.command()
@click.argument(u"target", type=click.Choice(field_groups), required=False)
def create(target):
    """Add field definitions to the schema.

    """
    target = [target] if target else field_groups
    Solr().create_schema(target)
    click.secho(u"Done", fg=u"green")


def get_commands():
    return [search_schema]
