# -*- coding: utf-8 -*-

import os
from ckan.common import json
import ckan.plugins as p
import ckanext.managed_search_schema.cli as cli


class ManagedSearchSchemaPlugin(p.SingletonPlugin):
    p.implements(p.ISearchSchema)
    p.implements(p.IClick)

    # ISearchSchema

    def update_search_schema_definitions(self, definitions):
        groups = u"field-type", u"field", u"dynamic-field", "copy-field"
        here = os.path.dirname(__file__)
        for group in groups:
            with open(os.path.join(here, u"schemas", group + u".json")) as fp:
                definitions[group].extend(
                    json.load(fp)
                )

    # IClick

    def get_commands(self):
        return cli.get_commands()
